import asyncio
import re
import os
from random import random

import aiohttp
import flickrapi
from PIL import ImageFont, ImageDraw, Image
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from rutermextract import TermExtractor
from wtforms import StringField
from wtforms.validators import DataRequired

from global_variables import *

# configure flask application
app = Flask(__name__)
app.config.update(dict(
    SECRET_KEY=APP_SECRET_KEY,
    WTF_CSRF_SECRET_KEY=APP_WTF_CSRF_SECRET_KEY,
    UPLOAD_FOLDER=UPLOAD_FOLDER,
    SQLALCHEMY_DATABASE_URI=DATABASE_URI,
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,
))

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
flickr = flickrapi.FlickrAPI(API_KEY, API_PASSWORD, cache=True)

# Keywords extractor
term_extractor = TermExtractor()

# font setting up
font = ImageFont.truetype(FONTPATH, 64)


def clear_log():
    # clear image folder before starting
    for img in os.listdir(app.config['UPLOAD_FOLDER']):
        if os.path.isfile(os.path.join(app.config['UPLOAD_FOLDER'], img)):
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], img))


def insert_to_db(full_text: str, terms: list) -> None:
    """
        full_text - string variable, entered text
        terms - string variable, keywords
        Insert full_text and keywords in database
    """
    found_sentence = SentencesAndKeywords.query.filter_by(sentence=full_text).all()
    if not found_sentence:
        add_data = SentencesAndKeywords(full_text, ", ".join(terms))
        db.session.add(add_data)
        db.session.commit()


async def async_get_images(terms: dict):
    tasks = []

    async with aiohttp.ClientSession() as session:
        for key, value in terms.items():
            if key == 'full_text':
                continue

            for url in value:
                task = asyncio.create_task(fetch_content(url, session, key, terms['full_text']))
                tasks.append(task)

        await asyncio.gather(*tasks)


async def fetch_content(url, session, keyword, full_text):
    async with session.get(url, allow_redirects=True) as response:
        data = await response.read()
        save_image(data, keyword, full_text)


def save_image(data, keyword, full_text):
    filepath = os.path.join('./', f'static/images/{keyword}_{random()}.jpg')

    with open(filepath, 'wb') as file:
        file.write(data)

    # Resize the image and insert the full text, then overwrite it
    image = Image.open(filepath)
    image = image.resize((1920, 1080), Image.ANTIALIAS).convert('RGB')
    draw_description(image, full_text)
    image.save(filepath)


def draw_description(img_pil, description: str) -> None:
    draw = ImageDraw.Draw(img_pil)
    draw.text((20, 1000), description, font=font, fill=(B, G, R, A))


def get_links(keyword: str) -> list:
    """
            keyword - sting variable
            full_text - string variable
            Download images by keyword and drawing full_text on its
        """
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
        if correct_urls > 5:  # six images are enough
            break

    return urls


class MyForm(FlaskForm):
    input_data = StringField(u'Введите слово или предложение:', validators=[DataRequired()])


@app.before_first_request
def create_table():
    """
        before first request we must create a database
    """
    db.create_all()


@app.route('/', methods=('GET', 'POST'))
def greetings_page():
    """
        The main page for input sentences
    """
    form = MyForm()
    if form.validate_on_submit():
        clear_log()
        text = form.input_data.data
        terms_ = {'full_text': text}
        for term in term_extractor(text, nested=True):
            if term.normalized not in terms_:
                terms_[term.normalized] = get_links(term.normalized)

        # Download image from the url and save it
        asyncio.run(async_get_images(terms_))
        terms = [term for keyword, term in terms_.items() if keyword != 'full_text']
        insert_to_db(text, terms)

        show = ['images/' + f for f in os.listdir('./static/images') if
                os.path.isfile(os.path.join('./static/images', f))]
        return render_template('result.html', list_images=show)
    return render_template('index.html', form=form)


@app.route('/view')
def view():
    """
        Show database of entered sentences and their keywords
    """
    return render_template('view.html', values=SentencesAndKeywords.query.all())
