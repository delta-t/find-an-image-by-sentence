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



# Flickr api access key 
api_key = '6d9ae033d1c204dbdb9c1b46404589d5'
api_password = '147314892eaa2340'
flickr=flickrapi.FlickrAPI(api_key, api_password, cache=False)

app = Flask(__name__)
app.config.update(dict(
    SECRET_KEY="123",
    WTF_CSRF_SECRET_KEY="122"
))

UPLOAD_FOLDER = 'static/images/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/test.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['CACHE_TYPE'] = 'null'

db = SQLAlchemy(app)

class SentencesAndKeywords(db.Model):
    _id = db.Column("sentence_id", db.Integer, primary_key=True)
    sentence = db.Column("sentence", db.String(300))
    keywords = db.Column("keywords", db.String(100))

    def __init__(self, sentence, keywords):
        print(sentence, keywords)
        self.sentence = sentence
        self.keywords = keywords

# Keywords extractor
term_extractor = TermExtractor()
fontpath = "./fonts/Montserrat_bold.ttf"
font = ImageFont.truetype(fontpath, 64)
b,g,r,a = 0,255,0,0


def get_images(keyword: str, full_text: str) -> None:
    print(keyword)
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
        if correct_urls > 5:
            break

    # Download image from the url and save it
    for i, url in enumerate(urls):
        urllib.request.urlretrieve(url, f'./static/images/{keyword}_{i}.jpg')
        # Resize the image and overwrite it
        image = Image.open(f'./static/images/{keyword}_{i}.jpg')
        image = image.resize((1920, 1080), Image.ANTIALIAS).convert('RGB')
        draw_description(image, full_text)
        image.save(f'./static/images/{keyword}_{i}.jpg')

def draw_description(img_pil, description: str) -> None:
    draw = ImageDraw.Draw(img_pil)
    draw.text((20, 1000),  description, font = font, fill = (b, g, r, a))


class MyForm(FlaskForm):
    input_data = StringField(u'Введите слово или предложение:', validators=[DataRequired()])

@app.before_first_request
def create_table():
    db.create_all()

@app.before_request
def clear_upload_folder():
    for img in os.listdir(app.config['UPLOAD_FOLDER']):
        if os.path.isfile(os.path.join(app.config['UPLOAD_FOLDER'], img)):
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], img))

def insert_to_db(text, terms):
    found_sentence = SentencesAndKeywords.query.filter_by(sentence=text).all()
    if not found_sentence:
        add_data = SentencesAndKeywords(text, ", ".join(terms))
        db.session.add(add_data)
        db.session.commit()

@app.route('/', methods=('GET', 'POST'))
def greetings_page():
    form = MyForm()
    if form.validate_on_submit():
        print(form.input_data)
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
    return render_template('view.html', values=SentencesAndKeywords.query.all())
