from datetime import datetime, timedelta
from time import time
from random import choice
from hashlib import sha256
import base64
import os

from werkzeug.security import generate_password_hash, check_password_hash
from markdown2 import markdown
from captcha.image import ImageCaptcha
from flask import url_for
from flask_login import UserMixin
import jwt

from app import db, config, login


image = ImageCaptcha(fonts=[config["CAPTCHA_FONT_PATH"]])


class Section(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shortname = db.Column(db.String(64), index=True, unique=True)
    longname = db.Column(db.String(128), unique=True)
    articles = db.relationship('Article', backref='owner', lazy='dynamic')

    def __repr__(self):
        return 'Section <{}>'.format(self.shortname)


class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    html_body = db.Column(db.Text)
    markdown_body = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    tripcode = db.Column(db.String(128), index=True)
    title = db.Column(db.String(128))
    section_id = db.Column(db.Integer, db.ForeignKey('section.id'))
    poster_name = db.Column(db.String(64))
    description = db.Column(db.String())
    anonymous = db.Column(db.Boolean, default=True)

    def create_tripcode(self, password):
        self.tripcode = sha256(password.encode("utf-8")).hexdigest()[:19]

    def create_html(self):
        self.html_body = markdown(
            self.markdown_body,
            extras=config['MARKDOWN_EXTRAS']
        )

    def format_timestamp(self):
        self.formated_timestamp = self.timestamp.strftime('%Y-%m-%d %H:%M')

    def remove(self):
        db.session.delete(self)

    def __repr__(self):
        return 'Article <{}>'.format(self.id)


class CaptchaStore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hash = db.Column(db.String(128))
    value = db.Column(db.String(64))
    decided = db.Column(db.Boolean, default=False)
    image = db.Column(db.String(128))

    def remove_picture(self):
        os.remove("{}{}.png".format(
            config["CAPTCHA_IMAGE_PATH"],
            self.hash
        ))

    def create_picture(self):
        string = \
            'abcdefghijklmnopqrstuvwxyz1234567890'
        self.value = ''.join(choice(string) for i in range(6))
        self.hash = generate_password_hash(self.value)[-12:]
        if not os.path.exists(config['CAPTCHA_IMAGE_PATH']):
            os.mkdir(config['CAPTCHA_IMAGE_PATH'])
        image.write(
            self.value,
            "{}{}.png".format(
                config['CAPTCHA_IMAGE_PATH'],
                self.hash
            )
        )
        self.image = url_for(
            'base.static',
            filename='captcha/{}.png'.format(self.hash)
        )

    def remove(self):
        self.remove_picture()
        db.session.delete(self)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    privilege = db.Column(db.Integer, default=0)
    password_hash = db.Column(db.String(128), index=True)
    username = db.Column(db.String(64), unique=True, index=True)
    token = db.Column(db.String(32), index=True, unique=True)
    token_expiration = db.Column(db.DateTime)
    email = db.Column(db.String(64), unique=True, index=True)
    email_verifed = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_token(self, expires_in=3600):
        now = datetime.utcnow()
        if self.token and self.token_expiration > now + timedelta(seconds=60):
            return self.token
        self.token = base64.b64encode(os.urandom(24)).decode('utf-8')
        self.token_expiration = now + timedelta(seconds=expires_in)
        db.session.add(self)
        return self.token

    def revoke_token(self):
        self.token_expiration = datetime.utcnow() - timedelta(seconds=1)

    def get_email_confirmation_token(self, expires_in=600):
        return jwt.encode(
            {'confirm_email': self.id, 'exp': time() + expires_in},
            config['SECRET_KEY'], algorithm='HS256'
        ).decode('utf-8')

    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
            config['SECRET_KEY'], algorithm='HS256'
        ).decode('utf-8')

    @staticmethod
    def check_token(token):
        user = User.query.filter_by(token=token).first()
        if user is None or user.token_expiration < datetime.utcnow():
            return None
        return user

    @staticmethod
    def verify_email_confirmation_token(token):
        try:
            id = jwt.decode(token, config['SECRET_KEY'],
                            algorithms=['HS256'])['confirm_email']
        except:
            return
        return User.query.get(id)

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, config['SECRET_KEY'],
                            algorithms=['HS256'])['reset_password']
        except:
            return
        return User.query.get(id)


@login.user_loader
def load_user(id):
    return User.query.get(int(id))
