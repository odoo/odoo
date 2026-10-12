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

# Dev Note exit codes should comply with https://www.unix.com/man-page/freebsd/3/sysexits/
# see http://www.postfix.org/aliases.5.html, output may end up in bounce mails
EX_USAGE = 64
EX_NOUSER = 67
EX_NOHOST = 68
EX_UNAVAILABLE = 69
EX_SOFTWARE = 70
EX_TEMPFAIL = 75
EX_NOPERM = 77
EX_CONFIG = 78


import sys
try:
    import traceback
    try:
        import xmlrpclib
    except ImportError:
        import xmlrpc.client as xmlrpclib
    import socket
    from optparse import OptionParser as _OptionParser
except ImportError as e:
    sys.stderr.write('%s\n' % e)
    sys.exit(EX_SOFTWARE)


class OptionParser(_OptionParser):
    def exit(self, status=0, msg=None):
        if msg:
            sys.stderr.write(msg)
        sys.stderr.write(" optparse status: %s\n" % status)
        sys.exit(EX_USAGE)


def postfix_exit(exit_code=EX_SOFTWARE, message=None, debug=False):
    try:
        if debug:
            traceback.print_exc(None, sys.stderr)
        if message:
            sys.stderr.write(message)
    except Exception:
        pass  # error handling failed, exit
    finally:
        sys.exit(exit_code)


def main():
    op = OptionParser(usage='usage: %prog [options]', version='%prog v1.3')
    op.add_option("-d", "--database", dest="database", help="Odoo database name (default: %default)", default='odoo')
    op.add_option("-u", "--userid", dest="userid", help="Odoo user id to connect with (default: %default)", default=1, type=int)
    op.add_option("-p", "--password", dest="password", help="Odoo user password (default: %default)", default='admin')
    op.add_option("--host", dest="host", help="Odoo host (default: %default)", default='localhost')
    op.add_option("--port", dest="port", help="Odoo port (default: %default)", default=8069, type=int)
    op.add_option("--proto", dest="protocol", help="Protocol to use (default: %default), http or https", default='http')
    op.add_option("--debug", dest="debug", action="store_true", help="Enable debug (may lead to stack traces in bounce mails)", default=False)
    op.add_option("--retry-status", dest="retry", action="store_true", help="Send temporary failure status code on connection errors.", default=False)
    (o, args) = op.parse_args()
    if args:
        op.print_help()
        sys.stderr.write("unknown arguments: %s\n" % args)
        sys.exit(EX_USAGE)
    if o.protocol not in ['http', 'https']:
        op.print_help()
        sys.stderr.write("unknown protocol: %s\n" % o.protocol)
        sys.exit(EX_USAGE)

    try:
        msg = sys.stdin.read()
        if sys.version_info > (3,):
            msg = msg.encode()
        models = xmlrpclib.ServerProxy('%s://%s:%s/xmlrpc/2/object' % (o.protocol, o.host, o.port), allow_none=True)
        models.execute_kw(o.database, o.userid, o.password, 'mail.thread', 'message_process', [False, xmlrpclib.Binary(msg)], {})
    except xmlrpclib.Fault as e:
        if e.faultString == 'Access denied' and e.faultCode == 3:
            postfix_exit(EX_NOPERM, debug=False)
        elif 'database' in e.faultString and 'does not exist' in e.faultString and e.faultCode == 1:
            postfix_exit(EX_CONFIG, "database does not exist: %s\n" % o.database, o.debug)
        elif 'No possible route' in e.faultString and e.faultCode == 1:
            postfix_exit(EX_NOUSER, "alias does not exist in odoo\n", o.debug)
        else:
            postfix_exit(EX_SOFTWARE, "xmlrpclib.Fault\n", o.debug)
    except (socket.error, socket.gaierror) as e:
        postfix_exit(
            exit_code=EX_TEMPFAIL if o.retry else EX_NOHOST,
            message="connection error: %s: %s (%s)\n" % (e.__class__.__name__, e, o.host),
            debug=o.debug,
        )
    except Exception:
        postfix_exit(EX_SOFTWARE, "", o.debug)

try:
    if __name__ == '__main__':
        main()
except Exception:
    # Handle all unhandled exceptions to prevent postfix from sending
    # a bounce mail that includes the invoked command with args which
    # may include the password for the odoo user.
    postfix_exit(EX_SOFTWARE, "", True)
