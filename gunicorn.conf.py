import openerp
# Standard OpenERP XML-RPC port.
bind = '127.0.0.1:8069'
# Some application-wide initialization is needed.
on_starting = openerp.wsgi.on_starting
# This is the big TODO: safely use more than a single worker.
workers = 1
