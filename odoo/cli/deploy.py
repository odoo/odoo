#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import os
import requests
import sys
import tempfile
import zipfile

from . import Command

class Deploy(Command):
    """Deploy a module on an Odoo instance"""
    def __init__(self):
        super(Deploy, self).__init__()
        self.session = requests.session()

    def deploy_module(self, module_path, url, login, password, db='', force=False):
        url = url.rstrip('/')
        csrf_token = self.authenticate(url, login, password, db)
        module_file = self.zip_module(module_path)
        try:
            return self.upload_module(url, module_file, force=force, csrf_token=csrf_token)
        finally:
            os.remove(module_file)

    def upload_module(self, server, module_file, force=False, csrf_token=None):
        print("Uploading module file...")
        url = server + '/base_import_module/upload'

        post_data = {'force': '1' if force else ''}
        if csrf_token: post_data['csrf_token'] = csrf_token

        with open(module_file, 'rb') as f:
            res = self.session.post(url, files={'mod_file': f}, data=post_data)
        res.raise_for_status()

        return res.text

    def authenticate(self, server, login, password, db=''):
        print("Authenticating on server '%s' ..." % server)

        # Fixate session with a given db if any
        self.session.get(server + '/web/login', params=dict(db=db))

        args = dict(login=login, password=password, db=db)
        res = self.session.post(server + '/base_import_module/login', args)
        if res.status_code == 404:
            raise Exception("The server '%s' does not have the 'base_import_module' installed." % server)
        elif res.status_code != 200:
            raise Exception(res.text)

        return res.headers.get('x-csrf-token')

    def zip_module(self, path):
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

    def run(self, cmdargs):
        parser = argparse.ArgumentParser(
            prog="%s deploy" % sys.argv[0].split(os.path.sep)[-1],
            description=self.__doc__
        )
        parser.add_argument('path', help="Path of the module to deploy")
        parser.add_argument('url', nargs='?', help='Url of the server (default=http://localhost:8069)', default="http://localhost:8069")
        parser.add_argument('--db', dest='db', help='Database to use if server does not use db-filter.')
        parser.add_argument('--login', dest='login', default="admin", help='Login (default=admin)')
        parser.add_argument('--password', dest='password', default="admin", help='Password (default=admin)')
        parser.add_argument('--verify-ssl', action='store_true', help='Verify SSL certificate')
        parser.add_argument('--force', action='store_true', help='Force init even if module is already installed. (will update `noupdate="1"` records)')
        if not cmdargs:
            sys.exit(parser.print_help())

        args = parser.parse_args(args=cmdargs)

        if not args.verify_ssl:
            self.session.verify = False

        try:
            if not args.url.startswith(('http://', 'https://')):
                args.url = 'https://%s' % args.url
            result = self.deploy_module(args.path, args.url, args.login, args.password, args.db, force=args.force)
            print(result)
        except Exception, e:
            sys.exit("ERROR: %s" % e)
