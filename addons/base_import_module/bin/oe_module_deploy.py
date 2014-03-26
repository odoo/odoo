#!/usr/bin/env python
import argparse
import os
import sys
import tempfile
import zipfile


try:
    import requests
except ImportError:
    # no multipart encoding in stdlib and this script is temporary
    sys.exit("This script requires the 'requests' module. ( pip install requests )")

session = requests.session()

def deploy_module(module_path, url, login, password, db=None):
    if url.endswith('/'):
        url = url[:-1]
    authenticate(url, login, password, db)
    check_import(url)
    module_file = zip_module(module_path)
    try:
        return upload_module(url, module_file)
    finally:
        os.remove(module_file)

def check_import(server):
    url = server +'/base_import_module/check' 
    res = session.get(url)
    if res.status_code == 404:
        raise Exception("The server %r does not have the 'base_import_module' installed." % server)
    elif res.status_code != 200:
        raise Exception("Server %r returned %s http error.", (server, res.status_code))

def upload_module(server, module_file):
    print("Uploading module file...")
    url = server + '/base_import_module/upload'
    files = dict(mod_file=open(module_file, 'rb'))
    res = session.post(url, files=files)
    if res.status_code != 200:
        raise Exception("Could not authenticate on server %r" % server)
    return res.text

def authenticate(server, login, password, db):
    print("Connecting to server %r" % server)
    print("Waiting for server authentication...")
    if db:
        url = server + '/login'
        args = dict(db=db, login=login, key=password)
        res = session.get(url, params=args)
    else:
        url = server + '/web/login'
        args = dict(login=login, password=password)
        res = session.post(url, args)
    if res.status_code != 200:
        raise Exception("Could not authenticate to OpenERP server %r" % server)

def zip_module(path):
    path = os.path.abspath(path)
    if not os.path.isdir(path):
        raise Exception("Could not find module directory %r" % path)
    container, module_name = os.path.split(path)
    temp = tempfile.mktemp(suffix='.zip')
    try:
        print("Zipping module directory...")
        with zipfile.ZipFile(temp, 'w') as zfile:
            for root, dirs, files in os.walk(path):
                for file in files:
                    file_path = os.path.join(root, file)
                    zfile.write(file_path, file_path.split(container).pop())
            return temp
    except Exception:
        os.remove(temp)
        raise

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Deploy a module on an OpenERP server.')
    parser.add_argument('path', help="Path of the module to deploy")
    parser.add_argument('--url', dest='url', help='Url of the server (default=http://localhost:8069)', default="http://localhost:8069")
    parser.add_argument('--database', dest='database', help='Database to use if server does not use db-filter.')
    parser.add_argument('--login', dest='login', default="admin", help='Login (default=admin)')
    parser.add_argument('--password', dest='password', default="admin", help='Password (default=admin)')
    parser.add_argument('--no-ssl-check', dest='no_ssl_check', action='store_true', help='Do not check ssl cert')
    if len(sys.argv) == 1:
        sys.exit(parser.print_help())

    args = parser.parse_args()

    if args.no_ssl_check:
        session.verify = False

    try:
        result = deploy_module(args.path, args.url, args.login, args.password, args.database)
        print(result)
    except Exception, e:
        sys.exit("ERROR: %s" % e)
