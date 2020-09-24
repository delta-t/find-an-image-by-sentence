import os
import json
import cv2
import re
import traceback
import numpy as np
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, Response, abort
from PIL import ImageFont, ImageDraw, Image
from markupsafe import escape
from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import DataRequired
from werkzeug.utils import secure_filename
from rutermextract import TermExtractor
import flickrapi
import urllib
from PIL import Image


# Flickr api access key 

flickr=flickrapi.FlickrAPI(api_key, api_password, cache=True)

app = Flask(__name__)
app.config.update(dict(
    SECRET_KEY="123",
    WTF_CSRF_SECRET_KEY="122"
))
UPLOAD_FOLDER = 'static'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Keywords extractor
term_extractor = TermExtractor()


def get_images(keyword):
    # keyword = 'siberian husky'
    # keywords = str(keywords).strip().split(',')
    # for keyword in keywords:
    print(keyword)
    photos = flickr.walk(
                        text=keyword,
                        tag_mode='all',
                        tags=keyword,
                        extras='url_c',
                        per_page=50,           # may be you can try different numbers..
                        sort='relevance')

    urls = []
    correct_urls = 0
    for photo in photos:           
        url = photo.get('url_c')
        if url is not None:
            urls.append(url)
            correct_urls += 1
        if correct_urls > 5:
            break
    print (urls)
    # Download image from the url and save it
    for i, url in enumerate(urls):
        urllib.request.urlretrieve(url, f'./static/{keyword}_{i}.jpg')
        # Resize the image and overwrite it
        image = Image.open(f'./static/{keyword}_{i}.jpg') 
        image = image.resize((1920, 1080), Image.ANTIALIAS)
        draw_description(image, keyword)
        image.save(f'./static/{keyword}_{i}.jpg')

def draw_description(img_pil, description):
    # img = cv2.imread('./static/setosa.jpg')
    # print(img.shape)
    # img = cv2.resize(img, (1920, 1080))

    b,g,r,a = 0,255,0,0
    fontpath = "./fonts/Montserrat.ttf"
    
    font = ImageFont.truetype(fontpath, 32)
    # img_pil = Image.fromarray(img)
    draw = ImageDraw.Draw(img_pil)
    draw.text((50, 100),  description, font = font, fill = (b, g, r, a))


class MyForm(FlaskForm):
    name = StringField('name', validators=[DataRequired()])


@app.route('/', methods=('GET', 'POST'))
def greetings_page():
    form = MyForm()
    if form.validate_on_submit():
        # get_images(form.name.data)
        print(form.name)
        text = form.name.data
        for term in term_extractor(text, nested=True):
            get_images(term.normalized)
            print(term.normalized, term.count)
        return render_template('index.html', form=form, user_image='static/setosa.jpg')
    return render_template('index.html', form=form)

