import os

basedir = os.path.abspath(os.path.dirname(__name__))


class Config:
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    CAPTCHA_IMAGE_PATH = os.path.join(basedir, 'app/static/captcha/')
    CAPTCHA_FONT_PATH = os.environ.get('CAPTCHA_FONT_PATH') or \
        os.path.join(basedir, 'app/static/fonts/Roboto-Regular.ttf')
