# -*- coding: utf-8 -*-
# Import flask and teplate operators
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_security import SQLAlchemyUserDatastore, Security

app = Flask(__name__)
app.config.from_object('config') # config import from config.py

# Define the DB
db = SQLAlchemy(app)
from models import User, Role

# Setup Flask-Security
user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore)

from app.views.index import IndexView

IndexView.register(app)