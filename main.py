import os
import json
import traceback
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
from flask_sqlalchemy import SQLAlchemy
from global_variables import *


# configure flask application
app = Flask(__name__)
app.config.update(dict(
    SECRET_KEY=APP_SECRET_KEY,
    WTF_CSRF_SECRET_KEY=APP_WTF_CSRF_SECRET_KEY
))
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# clear image folder before starting
for img in os.listdir(app.config['UPLOAD_FOLDER']):
    if os.path.isfile(os.path.join(app.config['UPLOAD_FOLDER'], img)):
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], img))

# database initialization
db = SQLAlchemy(app)

class SentencesAndKeywords(db.Model):
    _id = db.Column("sentence_id", db.Integer, primary_key=True)
    sentence = db.Column("sentence", db.String(300))
    keywords = db.Column("keywords", db.String(100))

    def __init__(self, sentence, keywords):
        print(sentence, keywords)
        self.sentence = sentence
        self.keywords = keywords


# flikr api initialization
flickr=flickrapi.FlickrAPI(API_KEY, API_PASSWORD, cache=True)

# Keywords extractor
term_extractor = TermExtractor()

# font setting up
font = ImageFont.truetype(FONTPATH, 64)


def insert_to_db(full_text: str, terms: str) -> None:
    '''
        full_text - string variable, entered text
        terms - string variable, keywords
        Insert full_text and keywords in database
    '''
    found_sentence = SentencesAndKeywords.query.filter_by(sentence=full_text).all()
    if not found_sentence:
        add_data = SentencesAndKeywords(full_text, ", ".join(terms))
        db.session.add(add_data)
        db.session.commit()

def get_images(keyword: str, full_text: str) -> None:
    '''
        keyword - sting variable
        full_text - string variable
        Download images by keyword and drawing full_text on its
    '''
    photos = flickr.walk(
                        text=keyword,
                        tag_mode='all',
                        tags=keyword,
                        extras='url_c',
                        per_page=50,
                        sort='relevance')

    urls = []
    correct_urls = 0
    for photo in photos:           
        url = photo.get('url_c')
        if url is not None:
            urls.append(url)
            correct_urls += 1
        if correct_urls > 5: # six images are enough
            break

    # Download image from the url and save it
    for i, url in enumerate(urls):
        urllib.request.urlretrieve(url, os.path.join('./', f'static/images/{keyword}_{i}.jpg'))
        # Resize the image and insert the full text, then overwrite it
        image = Image.open(os.path.join('./', f'static/images/{keyword}_{i}.jpg'))
        image = image.resize((1920, 1080), Image.ANTIALIAS).convert('RGB')
        draw_description(image, full_text)
        image.save(os.path.join('./', f'static/images/{keyword}_{i}.jpg'))

def draw_description(img_pil, description: str) -> None:
    draw = ImageDraw.Draw(img_pil)
    draw.text((20, 1000),  description, font = font, fill = (B, G, R, A))


class MyForm(FlaskForm):
    input_data = StringField(u'Введите слово или предложение:', validators=[DataRequired()])


@app.before_first_request
def create_table():
    '''
        before first request we must create a database
    '''
    db.create_all()


@app.route('/', methods=('GET', 'POST'))
def greetings_page():
    '''
        The main page for input sentences
    '''
    form = MyForm()
    if form.validate_on_submit():
        text = form.input_data.data
        terms = []
        for term in term_extractor(text, nested=True):
            get_images(term.normalized, text)
            terms.append(term.normalized)
        
        insert_to_db(text, terms)

        show = ['images/' + f for f in os.listdir('./static/images') if os.path.isfile(os.path.join('./static/images', f))]
        return render_template('index.html', form=form, list_images=show)
    return render_template('index.html', form=form)

@app.route('/view')
def view():
    '''
        Show database of entered sentences and their keywords
    '''
    return render_template('view.html', values=SentencesAndKeywords.query.all())
