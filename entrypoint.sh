#!/usr/bin/env bash
python manage.py makemigrations #  order blog shop
python manage.py migrate
# python manage.py createsuperuser --noinput

python manage.py collectstatic --noinput
#python manage.py runserver 0.0.0.0:8000
gunicorn backend.wsgi:application --bind 0.0.0.0:8000
