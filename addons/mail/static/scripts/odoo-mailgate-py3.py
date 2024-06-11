#!/usr/bin/env python3
# Part of Odoo. See LICENSE file for full copyright and licensing details.
#
# odoo-mailgate
#
# This program will read an email from stdin and forward it to odoo. Configure
# a pipe alias in your mail server to use it, postfix uses a syntax that looks
# like:
#
# email@address: "|/home/odoo/src/odoo-mail.py"
#
# while exim uses a syntax that looks like:
#
# *: |/home/odoo/src/odoo-mail.py
#
import argparse
import sys
import traceback
import xmlrpc.client

def main():
    parser = argparse.ArgumentParser(description='Script to handle incoming mail in Odoo. This script connects to an Odoo instance and processes incoming mail using the specified database, user credentials, and connection parameters.')
    parser.add_argument("-d", "--database", dest="database", help="Odoo database name (default: %(default)s)", default='odoo')
    parser.add_argument("-u", "--userid", dest="userid", help="Odoo user id to connect with (default: %(default)s)", default=1, type=int)
    parser.add_argument("-p", "--password", dest="password", help="Odoo user password (default: %(default)s)", default='admin')
    parser.add_argument("--host", dest="host", help="Odoo host (default: %(default)s)", default='localhost')
    parser.add_argument("--port", dest="port", help="Odoo port (default: %(default)s)", default=8069, type=int)
    args = parser.parse_args()

    try:
        msg = sys.stdin.buffer.read()  # Read as bytes
        models = xmlrpc.client.ServerProxy(f'http://{args.host}:{args.port}/xmlrpc/2/object', allow_none=True)
        models.execute_kw(args.database, args.userid, args.password, 'mail.thread', 'message_process', [False, xmlrpc.client.Binary(msg)], {})
    except xmlrpc.client.Fault as e:
        # reformat xmlrpc faults to print a readable traceback
        err = f"xmlrpc.client.Fault: {e.faultCode}\n{e.faultString}"
        sys.exit(err)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        sys.exit(2)

if __name__ == '__main__':
    main()
