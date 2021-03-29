# Импорт сторонних библиотек
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Config
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///candy_shop.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JSON_SORT_KEYS'] = False

db = SQLAlchemy(app)

# Импорт модулей
from shop_api import routes
