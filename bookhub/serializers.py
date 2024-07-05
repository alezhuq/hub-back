from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Genre, Book, BookRating, User
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from django.conf import settings


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    def validate_email(self, value):
        try:
            validate_email(value)
        except ValidationError:
            raise ValidationError("Invalid email address")
        return value

    class Meta:
        model = User
        fields = ('id', 'email', 'password', 'first_name', 'last_name', "likes")
        extra_kwargs = {'password': {'write_only': True},
                        "likes": {'write_only': True}
                        }

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            password=validated_data['password'],
            is_staff=False
        )
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, data):
        email = data.pop('email')
        password = data.pop('password')
        if not email or not password:
            raise serializers.ValidationError('Please provide both email and password.')
        user = authenticate(email=email, password=password)
        if not user:
            raise serializers.ValidationError('Invalid email or password.')
        refresh = RefreshToken.for_user(user)
        data['refresh'] = str(refresh)
        data['access'] = str(refresh.access_token)
        return data

    def get_token_backend(self):
        return settings.SIMPLE_JWT['AUTH_TOKEN_CLASSES'][0]

    def encode_jwt(self, payload):
        token_backend = self.get_token_backend()
        key = token_backend.get_private_key()
        return token_backend.encode(payload, key)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        refresh_token = representation['refresh']
        access_token = representation['access']
        payload = {'refresh': refresh_token, 'access': access_token}
        representation['jwt'] = self.encode_jwt(payload)
        return representation


class MainUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", 'first_name', 'email', 'password', 'last_name', "likes", ]
        extra_kwargs = {'password': {'write_only': True}}


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ('id', 'name')


class BookSerializer(serializers.ModelSerializer):
    likesCount = serializers.SerializerMethodField()
    sharesCount = serializers.SerializerMethodField()
    genreName = serializers.SerializerMethodField()
    authorFirstName = serializers.SerializerMethodField()
    authorLastName = serializers.SerializerMethodField()
    picture = serializers.ImageField()
    pdfFile = serializers.FileField()

    def get_likesCount(self, obj):
        return obj.likes.count()

    def get_sharesCount(self, obj):
        return obj.shares.count()

    def get_genreName(self, obj):
        return obj.genre.name if obj.genre else None

    def get_authorFirstName(self, obj):
        return obj.author.first_name if obj.author else None

    def get_authorLastName(self, obj):
        return obj.author.last_name if obj.author else None

    class Meta:
        model = Book
        fields = (
            'id', 'title', 'description', 'pdfFile', "author", 'size', "genre", 'genreName', "picture", 'likesCount',
            'sharesCount', 'authorFirstName', 'authorLastName')
        extra_kwargs = {
            'likes': {'read_only': True},
            'shares': {'read_only': True},
            'genre': {'write_only': True},
            'author': {'write_only': True},
        }


class BookLikeSerializer(serializers.ModelSerializer):
    class Meta:
        liked = serializers.BooleanField()
        model = Book
        fields = ('id', 'liked')


class BookRatingSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    user_lastname = serializers.SerializerMethodField()

    def get_user_name(self, obj):
        return obj.user.first_name

    def get_user_lastname(self, obj):
        return obj.user.last_name

    class Meta:
        model = BookRating
        fields = ('id', 'book', 'grade', 'reading_time', "comment", "user", "user_name", "user_lastname")

        extra_kwargs = {
            'book':{'read_only': True},
            "user":{'read_only': True},
        }


class BookSingleSerializer(serializers.ModelSerializer):
    likesCount = serializers.SerializerMethodField()
    sharesCount = serializers.SerializerMethodField()
    genreName = serializers.SerializerMethodField()
    authorFirstName = serializers.SerializerMethodField()
    authorLastName = serializers.SerializerMethodField()
    picture = serializers.ImageField()
    pdfFile = serializers.FileField()
    ratings = BookRatingSerializer(many=True)
    is_liked = serializers.SerializerMethodField()

    def get_likesCount(self, obj):
        return obj.likes.count()

    def get_sharesCount(self, obj):
        return obj.shares.count()

    def get_genreName(self, obj):
        return obj.genre.name if obj.genre else None

    def get_authorFirstName(self, obj):
        return obj.author.first_name if obj.author else None

    def get_authorLastName(self, obj):
        return obj.author.last_name if obj.author else None

    def get_is_liked(self, obj):
        request = self.context.get('request', None)
        if request and hasattr(request, 'user'):
            return request.user in obj.likes.all()
        return False

    class Meta:
        model = Book
        fields = (
            'id', 'title', 'description', 'pdfFile', "author", 'size', "genre", 'genreName', "picture", 'likesCount',
            'sharesCount', 'authorFirstName', 'authorLastName', 'ratings', "is_liked")
        extra_kwargs = {
            'likes': {'read_only': True},
            'shares': {'read_only': True},
            'genre': {'write_only': True},
            'author': {'write_only': True},
            'is_liked': {'read_only': True, "required": False},
        }