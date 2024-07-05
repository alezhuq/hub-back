from django.contrib import admin
from .models import BookRating, Genre, Book, User

# Register your models here.


admin.site.register(BookRating)
admin.site.register(User)
admin.site.register(Genre)
admin.site.register(Book)
