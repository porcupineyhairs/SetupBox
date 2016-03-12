# -*- coding: utf-8 -*-
# TODO: 디렉토리 겹쳐지는 문제 해결해야 함
import hashlib
import shutil
import urllib

import sys

from filesystem import *
from flask import Flask, render_template, request, redirect, url_for, send_file
from flask.ext.bower import Bower
from flask.ext.login import user_logged_in
from flask.ext.mail import Mail
from flask.ext.security import UserMixin, RoleMixin, SQLAlchemyUserDatastore, Security, current_user, user_registered
from flask_login import login_user
from flask_security import http_auth_required, login_required
from flask_sqlalchemy import SQLAlchemy
from os import error
from werkzeug.utils import secure_filename


app = Flask(__name__) # init flask app
app.config.from_object('config') # config import from config.py

# Define the flask-bower
bower = Bower(app)

# Define the DB
db = SQLAlchemy(app)

# Define mail
mail = Mail(app)

# Define models
roles_users = db.Table('roles_users',
        db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
        db.Column('role_id', db.Integer(), db.ForeignKey('role.id')))


# Role table
class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))


# User's table
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean())
    confirmed_at = db.Column(db.DateTime())
    roles = db.relationship('Role', secondary=roles_users,
                            backref=db.backref('users', lazy='dynamic'))

# Setup Flask-Security
user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore)

FILES_ROOT = app.config["FILES_ROOT"]

root_dir_of_user = ''

@app.before_first_request
def init():
    if current_user.is_authenticated:
        global root_dir_of_user
        root_dir_of_user = os.path.join(FILES_ROOT, current_user.email)

@user_logged_in.connect_via(app)
def when_user_logged_in(app, user):
    global root_dir_of_user
    root_dir_of_user = os.path.join(FILES_ROOT, user.email)


@user_registered.connect_via(app)
def when_user_registered(app, user):
    global root_dir_of_user

    root_dir_of_user = os.path.join(FILES_ROOT, user.email)

    if isdir(root_dir_of_user):
        os.mkdir(root_dir_of_user)


# for linux client auth
@app.route('/authTest')
@http_auth_required
def authTest():
    auth_info = request.authorization

    user = user_datastore.get_user(auth_info['username'])

    login_user(user)
    return user.get_auth_token()


# Index view
@app.route('/')
def index():
    return redirect(url_for('security.login'))


@app.route('/explorer')
@app.route('/files/<path:path>')
@login_required
def explorer(path=''):
    # 유저의 파일을 담는 루트 디렉토리를 정의
    email = current_user.email
    size = 20
    default = url_for('static',filename='ico/favicon.png')

    # construct the url
    gravatar_url = "http://www.gravatar.com/avatar/" + hashlib.md5(email.lower()).hexdigest() + "?"
    gravatar_url += urllib.urlencode({'d':default, 's':str(size)})

    # 받아온 경로와 원래 경로를 합침
    path_join = os.path.join(root_dir_of_user, path)

    if os.path.isdir(path_join):
        folder = Folder(root_dir_of_user, path)
        folder.read()
        return render_template('folder.html', gravatar_url=gravatar_url, folder=folder)
    else:
        my_file = File(root_dir_of_user, path)
        context = my_file.apply_action(View)
        folder = Folder(root_dir_of_user, my_file.get_path())

        if context == None:
           return send_file(os.path.join(root_dir_of_user,path))

        return render_template('file_view.html', gravatar_url=gravatar_url, text = context['text'], file=my_file, folder=folder)


@app.route('/search', methods=['POST'])
@login_required
def search():
    q = request.form['q']
    return render_template('search.html', request = q)


@app.route('/new_directory', methods=["POST"])
@app.route('/<path:path>/new_directory', methods=["POST"])
@login_required
def create_directory(path = ''):
    dirname = request.form["new_directory_name"]
    directory_root = request.form["directory_root"]

    try:
        os.mkdir(os.path.join(root_dir_of_user,directory_root,dirname))
    except error:
        print error.args

    return redirect(url_for('explorer', path = os.path.join(directory_root,dirname)))


@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if request.method == "POST":
        file = request.files['file']
        directory_root = request.form['directory_root']

        if file:
            filename = secure_filename(file.filename)

            path = os.path.join(root_dir_of_user,directory_root,filename)

            file.save(path)

        return redirect(url_for('explorer', path=os.path.join(directory_root)))


@app.route('/rename', methods=['POST'])
@login_required
def file_rename():
    if request.method == "POST":
        new_name = request.form['new_name'] # 파일의 새 이름

        directory_root = request.form['directory_root'] # 현재 디렉토리
        path = request.form['path'] # post 요청으로 전달된 파일의 경로

        old_name_path = os.path.join(root_dir_of_user, path)

        new_name_path = path.split('/')[:-1] # 원래 경로에서 이전 파일 이름만 제거하고 짜름
        new_name_path.append(new_name) # 새로 받은 이름을 합침

        new_name_path = os.path.join(root_dir_of_user, '/'.join(new_name_path))

        os.rename(old_name_path, new_name_path)

        return redirect(url_for('explorer',path = os.path.join(directory_root)))


@app.route('/delete', methods=['POST'])
@login_required
def file_delete():
    if request.method == 'POST':
        path = request.form['path']
        directory_root = request.form['directory_root']

        path_join = os.path.join(root_dir_of_user, path)

        if os.path.isdir(path_join):
            shutil.rmtree(path_join)
        else:
            os.remove(path_join)

        return redirect(url_for('explorer',path = os.path.join(directory_root)))


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print "Please input mode"
        quit()

    if sys.argv[1] == "develop":
        app.run()
    elif sys.argv[1] == "deploy":
        app.run(host="0.0.0.0", port=int(8080))

