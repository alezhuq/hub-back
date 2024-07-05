import datetime
import json

import numpy as np
import pandas as pd
from django.http import JsonResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics
from rest_framework import status
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.generics import CreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view

from .models import Genre, Book, BookRating, User
from .permissions import IsSuperUserOrReadOnly, IsBookOwnerOrReadOnly, IsOwner, IsAccountOwner, IsAuthor
from .serializers import GenreSerializer, BookSerializer, BookRatingSerializer, UserSerializer, \
    LoginSerializer, MainUserSerializer, BookSingleSerializer

from django.db.models import Exists, OuterRef, Subquery
from sklearn.model_selection import train_test_split
from sklearn.metrics.pairwise import pairwise_distances
from django.db.models import Min

def predict_ratings(ratings, similarity):
    mean_user_rating = ratings.mean(axis=1)
    ratings_diff = (ratings - mean_user_rating[:, np.newaxis])
    return mean_user_rating[:, np.newaxis] + similarity.dot(ratings_diff) / np.array([np.abs(similarity).sum(axis=1)]).T


def scale_down_to_5(value, x):
    try:
        res = (value.total_seconds() / x.total_seconds()) * 5
    except ZeroDivisionError:
        res = 0

    return res


class UserRegistrationView(CreateAPIView):
    """
    API endpoint that allows users to be registered and email confirmation to be sent.
    """
    serializer_class = UserSerializer

    def create(self, request, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            likes = serializer.validated_data.get("likes", [])

            user = serializer.save()
            user.likes.add(*likes)

            # add liked books

            return Response("user was created", status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(CreateAPIView):
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():

            data = serializer.validated_data
            response_data = {
                'refresh_token': data['refresh'],
                "access": data["access"],
            }
            response = Response(response_data, status=status.HTTP_200_OK)
            return response
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserView(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAccountOwner]
    serializer_class = MainUserSerializer
    queryset = User.objects.select_related("likes")

    def get_object(self):
        # Get the user making the request
        user = self.request.user

        # Set the lookup field to the user's id
        self.lookup_field = 'user_id'  # Assuming 'user_id' is the field name in your User model

        # Return the user object
        return user


@api_view(('GET',))
def recommend(request):  # user_id
    if not request.user.is_authenticated:
        print(request.user)
        return Response(status=status.HTTP_401_UNAUTHORIZED)
    data = []
    all_users = User.objects.all()
    # Iterate over each user
    for user in all_users:
        # Annotate each Book object with information about whether the current user liked and/or shared the book
        books_with_user_interaction_info = Book.objects.annotate(
            liked_by_user=Exists(user.likes.filter(id=OuterRef('pk'))),
            shared_by_user=Exists(user.shares.filter(id=OuterRef('pk'))),
            grade=Subquery(
                BookRating.objects.filter(user=user, book=OuterRef('pk')).values('grade')[:1]
            ),
            reading_time=Subquery(
                BookRating.objects.filter(user=user, book=OuterRef('pk')).values("reading_time")[:1]
            )
        ).values('id', 'liked_by_user', 'shared_by_user', "grade", 'reading_time')

        # Append the information for each book to the data list
        for book in books_with_user_interaction_info:
            data.append({
                'user_id': user.id,
                'book_id': book['id'],
                'like': book['liked_by_user'],
                'share': book['shared_by_user'],
                'grade': book['grade'],
                'reading_time': book['reading_time'],
            })
    min_book_id = Book.objects.aggregate(min_id=Min('id'))['min_id'] - 1
    # Create a pandas DataFrame from the data list
    df = pd.DataFrame(data)
    df['reading_time'] = df["reading_time"].apply(scale_down_to_5, args=(df['reading_time'].max(),))
    df = df.fillna(0)
    print(df)
    data_matrix = np.zeros((df["user_id"].max(), df["book_id"].max()))

    for line in df.itertuples():
        print(line)
        data_matrix[line[1] - 1, line[2] - 1] = line[3] + line[4] + line[5] + line[6]

    similarity = pairwise_distances(data_matrix, metric='cosine')
    prediction = predict_ratings(data_matrix, similarity)
    liked_books_ids = set(request.user.likes.values_list('id', flat=True))
    user_predicted_ratings = prediction[request.user.id - 1]

    books = list(Book.objects.all())
    print(len(books))
    book_ratings = []
    for book in books:
        if book.id not in liked_books_ids: 
            rating = user_predicted_ratings[book.id - 1]
            book_ratings.append({'book': book, 'rating': rating})

    print(book_ratings)
    book_ratings.sort(key=lambda x: x['rating'], reverse=True)

    # Extract sorted books
    sorted_books = [book_rating['book'] for book_rating in book_ratings]

    serializer = BookSerializer(sorted_books, many=True)
    return JsonResponse({"recommended_books": serializer.data})


class GenreListCreateView(generics.ListCreateAPIView):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    permission_classes = [IsSuperUserOrReadOnly]


class BookListMyView(generics.ListCreateAPIView):
    serializer_class = BookSerializer
    permission_classes = [IsAuthor]

    def get_queryset(self):
        return Book.objects.filter(author=self.request.user.id)


class BookListCreateView(generics.ListCreateAPIView):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ('genre',)
    search_fields = ('title', 'author__first_name', 'author__last_name')
    ordering_fields = ('title', 'author__first_name', 'author__last_name')
    permission_classes = [IsAuthenticatedOrReadOnly]

    def create(self, request, *args, **kwargs) -> Response:
        # Get the current user ID
        author_id = request.user.id if request.user.is_authenticated else None
        book_id = kwargs.get('pk')

        if not author_id:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        # Set the author ID in the request data
        request.data['author'] = author_id

        print(request.data)
        # Remove 'reading_time' from request data
        request.data.pop('reading_time', None)

        super().create(request, *args, **kwargs)
        return Response(status=status.HTTP_201_CREATED)


class BookRatingListCreateView(generics.ListCreateAPIView):
    queryset = BookRating.objects.all()
    serializer_class = BookRatingSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        # Set the current user as the user_id before saving
        serializer.save(user_id=self.request.user.id, book_id=self.kwargs.get('pk'))

    def create(self, request, *args, **kwargs) -> Response:
        # Get the current user ID
        if not request.user.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        # Set the author ID in the request data
        mutable_data = request.data.copy()
        # Set the author ID in the mutable data
        mutable_data = request.data.copy()
        book_id = kwargs.get('pk')
        if not book_id:
            return Response({'detail': 'Book ID not provided'}, status=status.HTTP_400_BAD_REQUEST)

        mutable_data['user_id'] = request.user.id
        mutable_data['book_id'] = book_id

        # Create the serializer with the modified data
        serializer = self.get_serializer(data=mutable_data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


# GET_PUT_DEL


class GenreRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer

    # create permission is superuser or read only
    permission_classes = [IsSuperUserOrReadOnly]


class BookRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Book.objects.all()
    serializer_class = BookSingleSerializer
    permission_classes = [IsBookOwnerOrReadOnly]

    # patch user likes book


class BookRatingRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = BookRating.objects.all()
    serializer_class = BookRatingSerializer
    permission_classes = [IsOwner]

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # Get the current reading_time from the instance
        current_reading_time = instance.reading_time

        # Get the new reading_time from the validated data, defaulting to 0 if not provided
        additional_reading_time = serializer.validated_data.get('reading_time', datetime.timedelta(seconds=0))

        # Ensure the new reading_time is a timedelta object
        if isinstance(additional_reading_time, int):
            additional_reading_time = datetime.timedelta(seconds=additional_reading_time)

        # Sum the current and new reading_time
        new_reading_time = current_reading_time + additional_reading_time

        # Update the grade and reading_time
        instance.grade = serializer.validated_data.get('grade', instance.grade)
        instance.reading_time = new_reading_time
        instance.save()

        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # Add up the reading_time from the request data to the existing reading_time
        new_reading_time = instance.reading_time + serializer.validated_data.get('reading_time',
                                                                                 datetime.timedelta(seconds=0))

        # Update the grade and reading_time
        instance.grade = serializer.validated_data.get('grade', instance.grade)
        instance.reading_time = new_reading_time
        instance.save()

        return super().update(request, *args, **kwargs)


class BookLikeView(APIView):
    def post(self, request, book_id):
        user = request.user
        try:
            book = Book.objects.get(id=book_id)
            if user in book.likes.all():
                # If user already likes the book, unlike it
                book.likes.remove(user)
                return Response({'message': 'Book unliked'}, status=status.HTTP_200_OK)
            else:
                # If user doesn't like the book, like it
                book.likes.add(user)
                return Response({'message': 'Book liked'}, status=status.HTTP_201_CREATED)
        except Book.DoesNotExist:
            return Response({'message': 'Book not found'}, status=status.HTTP_404_NOT_FOUND)


class BookShareView(APIView):
    def post(self, request, book_id):
        user = request.user
        try:
            book = Book.objects.get(id=book_id)
            if not (user in book.shares.all()):
                # If user doesn't like the book, like it
                book.shares.add(user)
            return Response({'message': 'Book shared'}, status=status.HTTP_201_CREATED)
        except Book.DoesNotExist:
            return Response({'message': 'Book not found'}, status=status.HTTP_404_NOT_FOUND)
