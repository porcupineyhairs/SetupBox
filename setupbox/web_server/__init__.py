# -*- coding: utf-8 -*-
"""
TODO:
1. 서버가 돌 때 ~/.setupbox 디렉토리가 있나 체크하고 없으면 만들기 --> 완료
2. 회원가입시 .setupbox 디렉토리 밑에 유저의 이메일로 된 디렉토리 만들기
"""
from filesystem import *
from flask import Flask, render_template, request, redirect, url_for
from flask.ext.security import UserMixin, RoleMixin, SQLAlchemyUserDatastore, Security
from flask.ext.bower import Bower
from flask_security import http_auth_required, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from os import error
from werkzeug.utils import secure_filename

app = Flask(__name__) # init flask app
app.config.from_object('config') # config import from config.py

# Define the flask-bower
bower = Bower(app)

# Define the DB
db = SQLAlchemy(app)

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


'''
브라우저로 접속하면 로그인을 해야 한다는 alert 창이 뜸
terminal 에서는 http -a <email:password> <URL> 입력할 것 (README 참고)
ex) http -a maxtortime@gmail.com:123456 127.0.0.1:5000/authTest
'''

# .setupbox 디렉토리가 없으면 만들 것
@app.before_first_request
def make_dir():
    # 유저들의 파일이 담길 폴더 경로
    app_path = os.path.expanduser('~/.setupbox')

    if not os.path.exists(app_path):
        os.mkdir(app_path)

# for linux client auth
@app.route('/authTest')
@http_auth_required
def authTest():
    return "LOGIN GOOD"


# index view
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/info')
def info():
    return render_template('info.html')


@app.route('/explorer')
@app.route('/files/<path:path>')
@login_required
def explorer(path=''):
    app.config.update(FILES_ROOT = os.path.join(os.path.expanduser('~/.setupbox/'),current_user.email))
    # 유저의 파일을 담는 루트 디렉토리를 정의
    FILES_ROOT = app.config['FILES_ROOT']

    # 회원가입된 유저의 이메일로된 디렉토리가 존재하지 않으면 그 디렉토리를 만든다
    if not os.path.exists(FILES_ROOT):
        os.mkdir(FILES_ROOT)

    # 받아온 경로와 원래 경로를 합침
    path_join = os.path.join(FILES_ROOT, path)

    if os.path.isdir(path_join):
        folder = Folder(FILES_ROOT, path)
        folder.read()
        return render_template('folder.html', folder=folder)
    else:
        my_file = File(FILES_ROOT, path)
        context = my_file.apply_action(View)
        folder = Folder(FILES_ROOT, my_file.get_path())

        if context == None:
            return render_template('file_unreadable.html', folder=folder)

        return render_template('file_view.html', text=context['text'], file=my_file, folder=folder)


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
    FILES_ROOT = app.config['FILES_ROOT']

    try:
        os.mkdir(os.path.join(FILES_ROOT,directory_root,dirname))
    except error:
        print error.args

    print directory_root
    return redirect('/files/' + directory_root)


# 현재는 모든 확장자를 업로드할 수 있음.
"""
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS
"""

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    FILES_ROOT = app.config['FILES_ROOT']

    if request.method == "POST":
        file = request.files['file']

        if file:
            filename = secure_filename(file.filename)
            directory_root = request.form['directory_root']
            path = os.path.join(FILES_ROOT,directory_root,filename)

            file.save(path)

            return redirect(url_for('explorer', path=os.path.join(directory_root)))
        else:
            return 'FILE UPLOAD FAILED'


@app.route('/rename', methods=['POST'])
@login_required
def file_rename():
    if request.method == "POST":
        return 'rename'


@app.route('/delete', methods=['POST'])
@login_required
def file_delete():
    FILES_ROOT = app.config['FILES_ROOT']

    if request.method == 'POST':
        path = request.form['path']
        directory_root = request.form['directory_root']

        os.remove(os.path.join(FILES_ROOT,path))

        # 왜 새로고침이 안 되지?
        return redirect(url_for('explorer',path = os.path.join(directory_root)))


if __name__ == '__main__':
    app.run()