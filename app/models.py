from app import db
from flask_login import UserMixin
from app import login
from werkzeug.security import generate_password_hash, check_password_hash
from app import login
import datetime
import time

class User(UserMixin, db.Model):

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    time = db.Column(db.Integer) #record latest update time

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def set_time(self):
        self.time = int(time.time())

class DeleteFile(db.Model):
    filename = db.Column(db.String(128), primary_key=True)
    username = db.Column(db.String(64), primary_key=True)
    filepath = db.Column(db.String(128))
    origname = db.Column(db.String(128))
    
    def __repr__(self):
        return 'DeleteFile {} {}'.format(self.filename, self.username)


@login.user_loader
def load_user(id):
    return User.query.get(int(id))

