import datetime

from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import UserManager


class User(AbstractUser):
    username = None

    REQUIRED_FIELDS = []
    email = models.EmailField(max_length=50, unique=True)
    USERNAME_FIELD = 'email'
    first_name = models.CharField(max_length=20)
    last_name = models.CharField(max_length=20)
    last_active = models.DateTimeField(blank=True, null=True)

    objects = UserManager()

    def __str__(self):
        return self.email


# Create your models here.

class Genre(models.Model):
    name = models.CharField(max_length=15)

    def __str__(self):
        return self.name


class Book(models.Model):
    title = models.CharField(max_length=25)
    description = models.TextField()
    pdfFile = models.FileField()
    size = models.PositiveIntegerField()
    genre = models.ForeignKey(Genre, on_delete=models.SET_NULL, null=True)
    likes = models.ManyToManyField(User, blank=True, related_name="likes")
    shares = models.ManyToManyField(User, blank=True, related_name="shares")
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="book_author")
    picture = models.ImageField()

    def __str__(self):
        return self.title


class BookRating(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="ratings")
    comment = models.TextField(max_length=2000, null =True, blank = True)
    grade = models.FloatField(null=True, blank=True)
    reading_time = models.DurationField(
        default=datetime.timedelta(days=0, hours=0, minutes=0, seconds=0, milliseconds=0, microseconds=0),null=True, blank=True)