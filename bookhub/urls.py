from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView, TokenObtainPairView

from .views import (
    GenreListCreateView, GenreRetrieveUpdateDestroyView,
    BookListCreateView, BookRetrieveUpdateDestroyView,
    BookRatingListCreateView, BookRatingRetrieveUpdateDestroyView, recommend, UserRegistrationView, LoginView,
    BookLikeView, BookShareView, UserView, BookListMyView,
)

urlpatterns = [
    path('login/', LoginView.as_view(), name='token_obtain_pair'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('register/', UserRegistrationView.as_view(), name='user_registration'),
    path('account/', UserView.as_view(), name='user_registration'),
    # path('accounts/', include('allauth.urls')),

    # Genre URLs
    path('genres/', GenreListCreateView.as_view(), name='genre-list-create'),
    path('genres/<int:pk>/', GenreRetrieveUpdateDestroyView.as_view(), name='genre-retrieve-update-destroy'),

    # Book URLs
    path('books/', BookListCreateView.as_view(), name='book-list-create'),
    path('books/my/', BookListMyView.as_view(), name='book-list-create'),
    path('books/<int:pk>/', BookRetrieveUpdateDestroyView.as_view(), name='book-retrieve-update-destroy'),

    # do route books/1/share/
    # BookRating URLs
    path('books/<int:pk>/rate/', BookRatingListCreateView.as_view(), name='bookrating-cr'),  # redo into route

    path('bookratings/<int:pk>/', BookRatingRetrieveUpdateDestroyView.as_view(), name='bookrating_rud'),

    path("books/<int:book_id>/like/", BookLikeView.as_view(), name="book_like"),
    path("books/<int:book_id>/share/", BookShareView.as_view(), name="book_share"),

    path("recommend/", recommend)

]