#!/usr/bin/env python2
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
# Note python2 was choosen on purpose for backward compatibility with old mail
# servers.
#
import optparse
import sys
import traceback
import xmlrpclib

def main():
    op = optparse.OptionParser(usage='usage: %prog [options]', version='%prog v1.2')
    op.add_option("-d", "--database", dest="database", help="Odoo database name (default: %default)", default='odoo')
    op.add_option("-u", "--userid", dest="userid", help="Odoo user id to connect with (default: %default)", default=1, type=int)
    op.add_option("-p", "--password", dest="password", help="Odoo user password (default: %default)", default='admin')
    op.add_option("--host", dest="host", help="Odoo host (default: %default)", default='localhost')
    op.add_option("--port", dest="port", help="Odoo port (default: %default)", default=8069, type=int)
    (o, args) = op.parse_args()

    try:
        msg = sys.stdin.read()
        models = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/2/object' % (o.host, o.port), allow_none=True)
        models.execute_kw(o.database, o.userid, o.password, 'mail.thread', 'message_process', [False, xmlrpclib.Binary(msg)], {})
    except xmlrpclib.Fault as e:
        # reformat xmlrpc faults to print a readable traceback
        err = "xmlrpclib.Fault: %s\n%s" % (e.faultCode, e.faultString)
        sys.exit(err)
    except Exception as e:
        traceback.print_exc(None, sys.stderr)
        sys.exit(2)

if __name__ == '__main__':
    main()
