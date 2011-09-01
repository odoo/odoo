import openerp
# Standard OpenERP XML-RPC port.
bind = '127.0.0.1:8069'
pidfile = '.gunicorn.pid'
# This is the big TODO: safely use more than a single worker.
workers = 2
# Some application-wide initialization is needed.
on_starting = openerp.wsgi.on_starting
when_ready = openerp.wsgi.when_ready
timeout = 240 # openerp request-response cycle can be quite long
