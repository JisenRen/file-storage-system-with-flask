#-*- coding:utf-8 -*-
from app import app
from flask import Flask, render_template, abort, send_from_directory, request, redirect, url_for, g, flash, session, make_response
from werkzeug.urls import url_quote
from app.forms import LoginForm, RegistrationForm
from flask_login import current_user, login_user, login_required, logout_user
from app.models import User, DeleteFile
from app import db, login
import os
from os import path
import shutil
import json
import time as t
from werkzeug.utils import secure_filename
from app.function import *
import requests
import paramiko

def accessible_path(path_name):
    if not current_user.is_authenticated:
        return 0
    dir_items = path_name.split('/')
    if len(dir_items) < 2:
        print("Wrong URL")
        abort(404)
    if dir_items[0] not in['users','recycle-bin'] or dir_items[1]!=current_user.username:
        print('This directory is not accessible to you. Please login again.')
        abort(404)
    return 1

@app.route('/')
def init():
    return render_template('base.html')

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

@app.before_request
def before_request():
    g.user = current_user

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        user_path = 'users/' + form.username.data
        t = user.time
        if t == None:
            time = '0'
        else:
            time = str(t)
        # Data = {'name':user.username, 'time':time}
        # requests.post('http://10.128.206.64:8080/sync', data = Data)
        user.set_time()
        db.session.commit()
        return redirect(url_for('index', path_name=user_path))

    return render_template('login.html', title='Sign In', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
	path = os.getcwd()
	if current_user.is_authenticated:
		return redirect('/')
	form = RegistrationForm()
	if form.validate_on_submit():
		user = User(username=form.username.data)
		user.set_password(form.password.data)
		db.session.add(user)
		db.session.commit()
		# Data = {'NAME':form.username.data, 'PASSWORD':form.password.data}
		# requests.post('http://10.128.206.64:8080/insert', data = Data)
		os.makedirs(path+'/users/'+form.username.data)
		os.makedirs(path+'/recycle-bin/'+form.username.data)
		flash('Congratulations, you are now a registered user!')
		return redirect(url_for('login'))
	return render_template('register.html', form=form)

@login_required
@app.route('/logout')
def logout():
	logout_user()
	session.clear()
	# print(current_user.username)
	return redirect(url_for('login'))

@login_required
@app.route('/delete_user')
def DeleteUser():
    user_path = './users/' + current_user.username
    shutil.rmtree(user_path)
    user_path = './recycle-bin/' + current_user.username
    shutil.rmtree(user_path)
    f = DeleteFile.query.filter_by(username = current_user.username).all()
    for ff in f:
        db.session.delete(ff)
    db.session.commit()
    f = User.query.filter_by(username = current_user.username).all()
    for ff in f:
        db.session.delete(ff)
    db.session.commit()
    return redirect(url_for('logout'))
    
    
@login_required
@app.route('/dir_index/<path:path_name>')
def index(path_name):
    while path_name[-1]=='/': path_name = path_name[:-1]
    if not accessible_path(path_name):
        return redirect('/logout')
    dpath = getcwd() + '/' + path_name   
    index_list, size, time = dirsearch(dpath, path_name)
    recycle_list = get_recycle_list(current_user.username)
    return render_template('index.html', list = index_list, path = path_name, recycle_list = recycle_list)

@login_required
@app.route('/c_index/<path:path_name>')
def cindex(path_name):
    while path_name[-1]=='/': path_name = path_name[:-1]
    if not accessible_path(path_name):
        return redirect('/logout')
    dpath = getcwd() + '/' + path_name   
    index_list, size, time = dirsearch(dpath, path_name)
    recycle_list = get_recycle_list(current_user.username)
    return json.dumps({'code':200, 'list':index_list, 'path':path_name, 'recycle_list':recycle_list})
    
@login_required
@app.route('/download/<path:file_path>')
def download(file_path):
    if not secure_path(file_path): abort(404)
    while file_path[-1]=='/': file_path = file_path[:-1]
    if not accessible_path(file_path):
        return redirect('/logout')
    dir_path = getcwd()
    if path.isfile(dir_path + '/' + file_path):
        dirpath, filename = path.split(dir_path + '/' + file_path)
        response = make_response(send_from_directory(dirpath, filename, as_attachment=True))
        response.headers["Filename"] = url_quote(filename)
        return response
    abort(404)

@login_required
@app.route('/upload/<path:dir_path>', methods=['POST'])    
def upload(dir_path):             
    if not accessible_path(dir_path):
        return redirect('/logout')
    if not secure_path(dir_path): abort(404)
    f = request.files['file']
            
    if f and valid_file(f.filename):
        while (dir_path[-1] == '/'): dir_path = dir_path[:-1]
        if not path.exists(dir_path):
            os.makedirs(dir_path)
        
        id = 1
        name, type = path.splitext(f.filename)
        type = type[1:]
        rn = name
        while path.exists(path.join(dir_path,f.filename)):
            f.filename = rn + '(%d)'%id + '.' + type
            id += 1
            
        f.save(path.join(dir_path,f.filename))
        return json.dumps({'code':200})
    else: abort(404)

@login_required
@app.route('/newfolder/<path:dir_path>', methods=['POST'])
def createfolder(dir_path):
    while dir_path[-1]=='/': dir_path = dir_path[:-1]
    if not accessible_path(dir_path):
        return redirect('/logout')
    dirname = request.json.get('name')
    root_dir = getcwd()
    oname = dirname
    id = 1
    while path.exists(root_dir+'/'+dir_path+'/'+dirname): 
        dirname = oname+'(%d)'%id
        id += 1
    mkdir(root_dir+'/'+dir_path+'/'+dirname)
    return json.dumps({'code':200})

@login_required    
@app.route('/delete/<path:file_path>', methods=["DELETE"])
def delete(file_path):       
    def relative_path(path, user):
        item = path.strip().split('/')
        path = '/'
        for j in range(2, len(item)): path += item[j] + '/'
        return path       
                 
    if not secure_path(file_path): abort(404)
    while file_path[-1]=='/': file_path = file_path[:-1]
    if not accessible_path(file_path):
        return redirect('/logout')
 
    target_path = './' + file_path
    try:
        o_name, backup_name = backup('./recycle-bin/' + current_user.username, target_path, None, 'b')
        if not path.isfile(target_path):
            shutil.rmtree(target_path)
        else: os.remove(target_path)
        rp = relative_path(parent(file_path), current_user.username)
        f = DeleteFile(filename = backup_name, origname = o_name, username = current_user.username, filepath = rp)
        db.session.add(f)
        db.session.commit()
        return json.dumps({'code':200});
        
    except OSError as err: 
        abort(404)

@login_required
@app.route('/restore/<path:file_path>', methods=["POST"])
def restore(file_path):        
    while file_path[-1]=='/': file_path = file_path[:-1]
    dpath = 'recycle-bin/' + current_user.username + '/' + file_path
    if not secure_path(dpath): abort(404)
    if not accessible_path(dpath):
        return redirect('/logout')
    try:
        dpath = './' + dpath    
        #target_path = get_original_path(current_user.username, file_path)
        f = DeleteFile.query.filter_by(username = current_user.username, filename = file_path).first()
        target_name = f.origname
        target_path = './users/' + current_user.username + f.filepath
        backup(target_path, dpath, target_name, 'r')
        if path.isfile(dpath):
            os.remove(dpath)
        else: shutil.rmtree(dpath)        
        #delete_dbs(current_user.username, file_path)
        db.session.delete(f)
        db.session.commit()
    except OSError as err:
        abort(404)
      
    return json.dumps({'code':200})
 
@login_required
@app.route('/remove/<path:file_path>', methods=["DELETE"])
def remove(file_path):
    while file_path[-1]=='/': file_path = file_path[:-1]
    dpath = 'recycle-bin/' + current_user.username + '/' + file_path
    if not secure_path(dpath):
        print('not secure') 
        abort(404)
    if not accessible_path(dpath):
        return redirect('/logout')
    dpath = './' + dpath
    try:    
        if path.isfile(dpath):
            os.remove(dpath)
        else: shutil.rmtree(dpath)
        f = DeleteFile.query.filter_by(username = current_user.username, filename = file_path).first()
        db.session.delete(f)
        db.session.commit()
    except OSError as err:
        abort(404)        
    return json.dumps({'code':200})

@app.route('/synchronize', methods=['POST'])
def autosync():
    if not current_user.is_authenticated:
        return redirect('/logout')
    ip = request.remote_addr
    Data = {'sync':'on','user':current_user.username}
    requests.post('http://'+ip+':8080/client', data = Data)
    return redirect('/')
    
@app.route('/dissynchronize', methods=['POST'])
def dissync():
    if not current_user.is_authenticated:
        return redirect('/logout')
    ip = request.remote_addr
    Data = {'sync':'off'}
    requests.post('http://'+ip+':8080/client', data = Data)
    return redirect('/')
    
@app.route('/insert', methods=['POST'])
def create_user():
    ip = '10.128.206.64'
    # if request.remote_addr != ip:
    #    return redirect('/logout')
    F = request.form
    user = User(username=F['NAME'])
    user.set_password(F['PASSWORD'])
    db.session.add(user)
    db.session.commit()
    os.makedirs('users/'+F['NAME'])   
    os.makedirs('recycle-bin/'+F['NAME'])
    return redirect(url_for('login'))

@app.route('/sync', methods=['POST'])
def synchronize():
    ip = '10.128.206.64'
    # if request.remote_addr != ip:
    #     return redirect('/logout')
    username = 'student'
    password = '31415926'
    ssh = login_ssh(ip, username, password)
    sftp = ssh.open_sftp()
    F = request.form
    sync_rec(sftp, 'users', F['name'], int(F['time']))
    sftp.close()
    return redirect(url_for('login'))        

@app.route('/search/<path:key>', methods=["GET"])
def search(key):
    if len(key.strip()) == 0 : return(json.dumps({'code':200, 'list':[]}))
    key_list = searching('./users/' + current_user.username, '', key)
    return json.dumps({'code':200, 'list':key_list})
