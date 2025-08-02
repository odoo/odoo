# Part of Odoo. See LICENSE file for full copyright and licensing details.
import argparse
import os
import requests
import sys
import tempfile
import zipfile
from pathlib import Path

from . import Command

class Deploy(Command):
    """Deploy a module on an Odoo instance"""
    def __init__(self):
        super(Deploy, self).__init__()
        self.session = requests.session()

    def deploy_module(self, module_path, url, login, password, db='', force=False):
        url = url.rstrip('/')
        module_file = self.zip_module(module_path)
        try:
            return self.login_upload_module(module_file, url, login, password, db, force=force)
        finally:
            os.remove(module_file)

    def login_upload_module(self, module_file, url, login, password, db, force=False):
        print("Uploading module file...")
        self.session.get(f'{url}/web/login?db={db}', allow_redirects=False)  # this set the db in the session
        endpoint = url + '/base_import_module/login_upload'
        post_data = {
            'login': login,
            'password': password,
            'db': db,
            'force': '1' if force else '',
        }
        with open(module_file, 'rb') as f:
            res = self.session.post(endpoint, files={'mod_file': f}, data=post_data)

        if res.status_code == 404:
            raise Exception(
                "The server '%s' does not have the 'base_import_module' installed or is not up-to-date." % url)
        res.raise_for_status()
        return res.text

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
            prog=f'{Path(sys.argv[0]).name} {self.name}',
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
        except Exception as e:
            sys.exit("ERROR: %s" % e)
