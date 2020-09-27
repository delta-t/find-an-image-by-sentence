FROM python

RUN pip install flask flask_sqlalchemy gunicorn flask_wtf Pillow flickrapi rutermextract

RUN mkdir /app
COPY . /app

WORKDIR /app