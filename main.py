#-*- coding: utf-8 -*-
from flask import Flask, render_template, abort, send_from_directory, request, redirect, url_for, g, flash, session
from config import Config
from flask_login import LoginManager, UserMixin
from app import app, db
from app.models import User

# u = User(username='alice', time='12345')
# db.session.add(u)
# db.session.commit()

# users = User.query.all()
# for u in users:
# 	print(u.id, u.username, u.time)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug = True)
