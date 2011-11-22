import openerp
# Standard OpenERP XML-RPC port.
bind = '127.0.0.1:8069'
pidfile = '.gunicorn.pid'
# This is the big TODO: safely use more than a single worker.
workers = 1
# Some application-wide initialization is needed.
on_starting = openerp.wsgi.on_starting
when_ready = openerp.wsgi.when_ready
timeout = 240 # openerp request-response cycle can be quite long

# Setting openerp.conf.xxx will be better than setting
# openerp.tools.config['xxx']
conf = openerp.tools.config
conf['addons_path'] = '/home/openerp/repos/addons/trunk-xmlrpc'
conf['static_http_document_root'] = '/tmp'
#conf['log_level'] = 10 # 10 is DEBUG
