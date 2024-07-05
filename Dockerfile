FROM python:3
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /code
COPY ./bookHubBack/requirements.txt /code/
RUN pip install -r requirements.txt
COPY ./bookHubBack /code/
EXPOSE 8000
RUN chmod +x /code/entrypoint.sh
