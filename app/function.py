# -*- coding: utf-8 -*-
import os
from flask import abort, redirect
from os import path, getcwd, mkdir, rmdir, remove, replace, listdir, makedirs
import time as t
from app.models import User, DeleteFile
import requests
import shutil
import paramiko

validtype = ['txt', 'pdf', 'doc', 'docx', 'bmp', 'jpg', 'jpeg', 'png', 'gif', 'cr2',
             'ppt', 'pptx', 'pps', 'ppsx', 'avi', 'mov', 'qt', 'asf', 'rm', 'mp4', 'mkv',
             'mp3', 'wav', 'xls', 'xlsx', 'zip', 'rar', '7z', 'iso', 'gz', 'z', 
             'ico', 'icon', 'html', 'css', 'js', 'py', 'c', 'cpp' ,'java']
             
def get_type(type):
    type = type.lower()[1:]
    if type in ['txt', 'pdf', 'iso']: return type
    if type in ['doc', 'docx']: return 'word'
    if type in ['bmp', 'jpg', 'jpeg', 'png', 'gif', 'cr2', 'ico', 'icon']: return 'image'
    if type in ['ppt', 'pptx', 'pps', 'ppsx']: return 'ppt'
    if type in ['avi', 'mov', 'qt', 'asf', 'rm', 'mp4', 'mkv']: return 'video'
    if type in ['mp3', 'wav']: return 'music'
    if type in ['xls', 'xlsx']: return 'excel'
    if type in ['zip', 'rar', '7z', 'gz', 'z']: return 'compression'
    return 'file'
    
def secure_path(path):
    return (path.find('..') == -1)

def login_ssh(ip,username,password,port = 22):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname = ip,port = port, username = username, password = password)
    return ssh
    
def sync_rec(sftp, root_path, dir_path, timestamp):
    try:
        if path.exists(root_path+'/'+dir_path):
            remote_list = sftp.listdir("simple-file-storage-with-Flask/" + root_path)
            if dir_path not in remote_list:
                sftp.mkdir("simple-file-storage-with-Flask/" + root_path + '/' + dir_path)
            fl = listdir(root_path+'/'+dir_path)
            for f in fl:
                str = root_path + '/' + dir_path + '/' + f
                if path.isfile(str):
                    info = os.stat(str)
                    if (info.st_mtime >= timestamp) or (info.st_ctime >= timestamp):
                        sftp.put(str, "simple-file-storage-with-Flask/" + str)
                else:
                    sync_rec(sftp, root_path + '/' + dir_path, f, timestamp)
                    
    except OSError as err:
        abort(405)
            
def normalsize(s):
    nexts = {'B':'K', 'K':'M', 'M':'G', 'G':'T'}
    ns = 'B'
    while s >=1024:
        s /= 1024
        ns = nexts[ns]
            
    return "%.4f"%s+ns
          
def dirsearch(dpath, cpath):
    if path.exists(dpath):
        index_list = []
        dsize = 0
        dtime = 0
        if path.isfile(dpath): abort(404)
        file_list = listdir(dpath)
        index_list = []
        idx = 1
        for file in file_list:
            ndpath = dpath+'/'+file
            ncpath = cpath+'/'+file
            if path.isfile(ndpath):
                try: 
                    size = path.getsize(ndpath)
                    time = path.getmtime(ndpath)
                    if time > dtime: dtime = time
                    dsize += size
                    size = normalsize(size)
                    if time == 0: time = '-------------------------'
                    else: time = TimeStampToTime(time)
                except OSError as err:
                    abort(404)
                    
                name, type = path.splitext(file)
                index_list.append([name, type[1:], get_type(type), idx, size, time])
            else:
                cl, size, time = dirsearch(ndpath, ncpath)
                dsize += size
                dtime += time
                if time > dtime: dtime = time
                dsize += size
                size = normalsize(size)
                if time == 0: time = '-------------------------'
                else: time = TimeStampToTime(time)
                index_list.append([file, 'dir', 'folder', idx, size, time])
            idx += 1
        return index_list, dsize, dtime    
    else: abort(404)

def get_recycle_list(usr):
    list = []
    if path.exists('./recycle-bin/' + usr):
        cyclepath = './recycle-bin/' + usr
        for file in listdir(cyclepath):
            f = DeleteFile.query.filter_by(username = usr, filename = file).first()
            oname = f.origname
            rpath = f.filepath
            if path.isfile(cyclepath+ '/' + file):
                name, type = path.splitext(oname)
                list += [[name, type[1:], get_type(type), rpath, file]]
            else:
                list += [[oname, 'dir', 'folder', rpath, file]]
                
        return list
    else: abort(404)
def TimeStampToTime(timestamp):
    timestruct = t.localtime(timestamp)
    return t.strftime('%Y-%m-%d %H:%M:%S',timestruct)    
                    
def parent(str):
    k = len(str) - 1
    while (k > 0) and (str[k] != '/'):
        k = k - 1
    return str[0:k]    

def valid_file(name):
    ext = name.rsplit('.',1)[1].lower()
    return (ext in validtype) and (name.find('\\')==-1 and name.find('/')==-1)

def merge(dest, src):
    if (path.isfile(dest)or path.isfile(src)):abort(404)
    for file in listdir(src):
        if path.isfile(src + '/' + file):
            shutil.copy2(src + '/' + file, dest + '/' + file)
        else:
            if path.exists(dest + '/' + file): merge(dest+'/'+file, src+'/'+file)
            else: shutil.copytree(src+'/'+file, dest+'/'+file)
    
def backup(rb, target, targetname, mode):
    try:
        if path.isfile(target):
            filename = path.basename(target)
            name, type = filename.rsplit('.', 1)
            type = type.lower()
            rname = name
            id = 1
            if mode == 'b': 
                while path.exists(rb + '/' + rname + '.' + type): 
                    rname = name + "(%d)"%id
                    id += 1
                
                rfile = rname + '.' + type
            if mode == 'r':
                shutil.copy2(target, rb + '/' + targetname)
                return
 
            if not path.exists(rb): makedirs(rb)
            shutil.copy2(target, rb + '/' + rfile)
            return filename, rfile
            
        else:
            while (target[-1] in ['\\','/']): target = target[:-1]
            dirname = path.basename(target)
            rname = dirname
            id = 1
            if mode == 'b':
                while path.exists(rb+ '/' + rname):
                    rname = dirname + "(%d)" % id
                    id += 1
            if mode == 'r':
                if path.exists(rb + '/' + targetname): merge(rb + '/' + targetname, target)
                else: shutil.copytree(target, rb + '/' + targetname)    
                return
                
            shutil.copytree(target, rb + '/' + rname)
            return dirname, rname
        
    except OSError as err:
        abort(404)

def searching(abspath, relpath, key):
    list = []
    queue = []
    try:
        for file in listdir(abspath):
            if not path.isfile(abspath+'/'+file):
                queue += [[relpath+'/'+file, abspath+'/'+file]]
                if key in file: list += [[file, 'folder', relpath+'/'+file, abspath]]
            else:
                if key in file: 
                    name, type = path.splitext(file)
                    list += [[file, get_type(type), relpath+'/'+file, abspath]]
                
        for relpath, abspath in queue:
            list += searching(abspath, relpath, key)
        return list            
    except OSError as err:
        abort(404)    
