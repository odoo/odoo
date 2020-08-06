#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import os
import requests
import sys
import tempfile
import zipfile
import odoo

session = requests.session()


def deploy_module(module_path, url, login, password, db='', force=False):
    url = url.rstrip('/')
    module_file = zip_module(module_path)
    try:
        return login_upload_module(module_file, url, login, password, db, force=force)
    finally:
        os.remove(module_file)


def login_upload_module(module_file, url, login, password, db, force=False):
    print("Uploading module file...")
    endpoint = url + '/base_import_module/login_upload'
    post_data = {
        'login': login,
        'password': password,
        'db': db,
        'force': '1' if force else '',
    }
    with open(module_file, 'rb') as f:
        res = session.post(endpoint, files={'mod_file': f}, data=post_data)

    if res.status_code == 404:
        raise Exception(
            "The server '%s' does not have the 'base_import_module' installed or is not up-to-date." % url)
    res.raise_for_status()
    return res.text


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


def main():
    if not odoo.config['deploy_verify_ssl']:
        session.verify = False

    try:
        if not args.url.startswith(('http://', 'https://')):
            args.url = 'https://%s' % args.url
        result = deploy_module(
            odoo.config['deploy_module_path'],
            odoo.config['deploy_url'],
            odoo.config['deploy_login'],
            odoo.config['deploy_pwd'],
            odoo.config['deploy_db'],
            force=odoo.config['deploy_force'],
        )
        print(result)
    except Exception as e:
        sys.exit("ERROR: %s" % e)
