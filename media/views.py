import pandas as pd
from rest_framework import status
from rest_framework.generics import RetrieveUpdateDestroyAPIView, CreateAPIView, ListCreateAPIView, ListAPIView
from django.db.models import F, Count, Case, When
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from sklearn.metrics.pairwise import cosine_similarity
from .models import Product, Rating, UserView, MainUser, Ban, Drug
from .permissions import IsOwner
from .serializers import ProductSerializer, RatingSerializer, MainUserSerializer, \
    ProductlistSerializer, BanSerializer, DrugIdSerializer  # UserViewSerializer


# Create your views here.

def recommend(user_id):
    if not Rating.objects.filter(user=user_id).exists():
        res = Product.objects.annotate(
            total_views=F('userview__view_count')
        ).order_by('-total_views')
    else:
        # filter out products with banned drugs
        banned_products = list(map(lambda x: int(x[0]),
                                   Product.objects.prefetch_related(
                                       "drug", "drug__ban",
                                   ).filter(
                                       drug__ban__user_id=user_id
                                   ).values_list("id")
                                   ))
        # rate = Rating.objects.exclude(product__id__in=banned_products).values()
        # print(banned_products)
        rate = Rating.objects.all().values()
        ratings_df = pd.DataFrame.from_records(
            rate
        )
        # pivot table
        pivot_table = ratings_df.pivot_table(values='rate', index='user_id', columns='product_id', fill_value=0)
        # print(pivot_table)
        filtered_table = pivot_table.drop(columns=banned_products)
        print(filtered_table)
        user_ratings = filtered_table.loc[user_id].values.reshape(1, -1)
        # sim users
        similarity = cosine_similarity(filtered_table.values, user_ratings)
        similar_users = similarity.argsort(axis=0)[-2:-1].flatten()
        # evaluate potential rating
        recommendations = filtered_table.iloc[similar_users].mean(axis=0).sort_values(ascending=False)[:10]
        preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(recommendations.index)])
        print(recommendations)
        res = Product.objects.filter(id__in=recommendations.index).order_by(preserved)
        # print(res)

    return res


class ProductListView(APIView):

    def get(self, request):
        products = Product.objects.all()
        serializer = ProductlistSerializer(products, many=True)
        res = Response()
        res.data = {"all": serializer.data}
        if request.user.is_authenticated:
            recommended = recommend(user_id=request.user.id)
            rec_serialized = ProductlistSerializer(recommended, many=True)
            res.data.update({"recommended": rec_serialized.data})

        return res


class ProductView(RetrieveUpdateDestroyAPIView):
    serializer_class = ProductSerializer
    queryset = Product.objects.prefetch_related("picture")

    def get(self, request, *args, **kwargs):
        # Get the product instance based on the URL parameter
        product_instance = self.get_object()

        # Check if the user is authenticated
        if request.user.is_authenticated:
            # Get the list of viewed product IDs from the session
            viewed_product_ids = request.session.get('viewed_product_ids', [])

            # Check if the product has already been viewed in the current session
            if product_instance.id not in viewed_product_ids:
                # Increment the session counter by 1
                request.session['product_views_count'] = request.session.get('product_views_count', 0) + 1

                # Update the list of viewed product IDs in the session
                viewed_product_ids.append(product_instance.id)
                request.session['viewed_product_ids'] = viewed_product_ids
                view, created = UserView.objects.get_or_create(user=request.user, product=product_instance)
                view.view_count = F("view_count") + 1
                view.save()

        return super().get(request, *args, **kwargs)


class RatingView(RetrieveUpdateDestroyAPIView):
    serializer_class = RatingSerializer

    def get_queryset(self):
        user_id = self.request.user.id
        product_id = self.kwargs.get('pk')
        return Rating.objects.filter(user=user_id, product=product_id)


class RatingCreateView(CreateAPIView):
    serializer_class = RatingSerializer

    # def get_queryset(self):
    #     user_id = self.request.user.id
    #     product_id = self.kwargs.get('pk')
    #     return Rating.objects.filter(user=user_id)
    def create(self, request, *args, **kwargs):
        user_id = self.request.user.id
        product_id = self.kwargs.get('pk')
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rating = Rating.objects.update_or_create(
            user_id=user_id,
            product_id=product_id,
        )
        return Response({"detail": "Rating created successfully."}, status=status.HTTP_201_CREATED)


class BanCreateView(APIView):
    def post(self, request, *args, **kwargs):
        data = request.data

        if not isinstance(data, list):
            return Response({'error': 'Invalid data format. Expected a list.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = BanSerializer(data=data, many=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# class RegisterView(CreateAPIView):
#     serializer_class = CustomRegisterSerializer
#     queryset = MainUser.objects.all()

class UserRegisterView(CreateAPIView):
    serializer_class = MainUserSerializer
    queryset = MainUser.objects.all()

    def perform_create(self, serializer):
        # Call the create_user method of your custom manager
        user = MainUser.objects.create_user(**serializer.validated_data)
        # Use the serializer to update the created user instance
        serializer.instance = user


# class UserViewView(RetrieveUpdateDestroyAPIView):
#     serializer_class = UserViewSerializer
#
#     def get_queryset(self):
#         user_id = self.kwargs.get('user_id')
#         return UserView.objects.filter(user=user_id)


class UsersView(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsOwner]
    serializer_class = MainUserSerializer
    queryset = MainUser.objects.all()


class DrugListView(ListAPIView):
    serializer_class = DrugIdSerializer
    queryset = Drug.objects.all()