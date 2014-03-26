#!/usr/bin/env python
import argparse
import os
import sys
import tempfile
import urllib
import urllib2
import zipfile

def deploy_module(module_path, url, login, password, db=None):
    if url.endswith('/'):
        url = url[:-1]
    module_file = zip_module(module_path)
    cookie = authenticate(url, login, password, db)
    upload_module(url, module_file, cookie)

def upload_module(server, module_file, cookie):
    pass

def authenticate(server, login, password, db):
    if db:
        args = dict(db=db, login=login, key=password)
        url = server + '/login?' + urllib.urlencode(args)
        req = urllib2.Request(url)
    else:
        url = server + '/web/login'
        args = dict(login=login, password=password)
        req = urllib2.Request(url, urllib.urlencode(args))
    response = urllib2.urlopen(req)
    if response.code != 200:
        raise Exception("Could not authenticate to OpenERP server %r" % server)
    cookie = response.headers.get('Set-Cookie')
    return cookie

def zip_module(path):
    path = os.path.abspath(path)
    if not os.path.isdir(path):
        raise Exception("Could not find module directory %r" % path)
    container, module_name = os.path.split(path)
    temp = tempfile.mktemp(suffix='.zip')
    temp = '/tmp/1/test.zip'
    with zipfile.ZipFile(temp, 'w') as zfile:
        for root, dirs, files in os.walk(path):
            for file in files:
                file_path = os.path.join(root, file)
                zfile.write(file_path, file_path.split(container).pop())
        return temp

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Deploy a module on an OpenERP server.')
    parser.add_argument('path', help="Path of the module to deploy")
    parser.add_argument('--url', dest='url', help='Url of the server (default=http://localhost:8069)', default="http://localhost:8069")
    parser.add_argument('--database', dest='database', help='Database to use if server does not use db-filter.')
    parser.add_argument('--login', dest='login', default="admin", help='Login (default=admin)')
    parser.add_argument('--password', dest='password', default="admin", help='Password (default=admin)')
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    args = parser.parse_args()
    deploy_module(args.path, args.url, args.login, args.password, args.database)
    # try:
    #     deploy_module(args.path, args.url, args.login, args.password, args.database)
    # except Exception, e:
    #     print(e)
    #     sys.exit(1)
