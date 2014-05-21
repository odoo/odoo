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

def deploy_module(module_path, url, login, password, db=''):
    url = url.rstrip('/')
    authenticate(url, login, password, db)
    module_file = zip_module(module_path)
    try:
        return upload_module(url, module_file)
    finally:
        os.remove(module_file)

def upload_module(server, module_file):
    print("Uploading module file...")
    url = server + '/base_import_module/upload'
    files = dict(mod_file=open(module_file, 'rb'))
    res = session.post(url, files=files)
    if res.status_code != 200:
        raise Exception("Could not authenticate on server '%s'" % server)
    return res.text

def authenticate(server, login, password, db=''):
    print("Authenticating on server '%s' ..." % server)

    # Fixate session with a given db if any
    session.get(server + '/web/login', params=dict(db=db))

    args = dict(login=login, password=password, db=db)
    res = session.post(server + '/base_import_module/login', args)
    if res.status_code == 404:
        raise Exception("The server '%s' does not have the 'base_import_module' installed." % server)
    elif res.status_code != 200:
        raise Exception(res.text)

def zip_module(path):
    path = os.path.abspath(path)
    if not os.path.isdir(path):
        raise Exception("Could not find module directory '%s'" % path)
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
    parser.add_argument('--db', dest='db', help='Database to use if server does not use db-filter.')
    parser.add_argument('--login', dest='login', default="admin", help='Login (default=admin)')
    parser.add_argument('--password', dest='password', default="admin", help='Password (default=admin)')
    parser.add_argument('--no-ssl-check', dest='no_ssl_check', action='store_true', help='Do not check ssl cert')
    if len(sys.argv) == 1:
        sys.exit(parser.print_help())

    args = parser.parse_args()

    if args.no_ssl_check:
        session.verify = False

    try:
        result = deploy_module(args.path, args.url, args.login, args.password, args.db)
        print(result)
    except Exception, e:
        sys.exit("ERROR: %s" % e)
