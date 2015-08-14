# WSGI Handler sample configuration file.
#
# Change the appropriate settings below, in order to provide the parameters
# that would normally be passed in the command-line.
# (at least conf['addons_path'])
#
# For generic wsgi handlers a global application is defined.
# For uwsgi this should work:
#   $ uwsgi_python --http :9090 --pythonpath . --wsgi-file openerp-wsgi.py
#
# For gunicorn additional globals need to be defined in the Gunicorn section.
# Then the following command should run:
#   $ gunicorn openerp:service.wsgi_server.application -c openerp-wsgi.py

import openerp

#----------------------------------------------------------
# Common
#----------------------------------------------------------
openerp.multi_process = True # Nah!

# Equivalent of --load command-line option
openerp.conf.server_wide_modules = ['web']
conf = openerp.tools.config

# Absolute path to the Odoo Addons base repository 
# (comma-separated for multiple locations)
BASE_PATH = '/home/nuobit/opt/nuobit/'

# Path to the Odoo Addons base repository (comma-separated for
ADDONS_REL_PATHS = [#'addons/misc', 
                    #'addons/l10n-spain', 
                    #'addons/partner-contact', 
                    #'addons/account-financial-tools',
                    #'addons/account-payment',
                    #'addons/product-attribute',
                    #'addons/bank-statement-import',
                    #'addons/bank-statement-reconcile',
                    #'addons/bank-payment',
                    #'addons/purchase-workflow',
                    'odoo/openerp/addons',
                    'odoo/addons',
                    ]

conf['addons_path'] = ','.join(['%s%s' % (BASE_PATH, x) for x in ADDONS_REL_PATHS])

# Optional database config if not using local socket
#conf['db_name'] = 'mycompany'
#conf['db_host'] = 'localhost'
#conf['db_user'] = ''        # put your db user here (f.e. base_odoo)
#conf['db_port'] = 5432
#conf['db_password'] = ''    # put your db user password here

#----------------------------------------------------------
# Generic WSGI handlers application
#----------------------------------------------------------
application = openerp.service.wsgi_server.application

openerp.service.server.load_server_wide_modules()

#----------------------------------------------------------
# Cron wsgi activation
# The next two lines allow cron automated tasks in a wsgi environment only. 
# they must be just after "load_server_wide_modules()" instruction.
# Exaple of cron task: fetching emails.
#----------------------------------------------------------
from openerp.service.server import ThreadedServer
ThreadedServer(None).cron_spawn()

#----------------------------------------------------------
# Webfaction
# Allows to use postgresql Webfaction shared database.
# webfaction_db_base:   It's an auxiliary database, it's mandatory and it'll be always empty.
#                       It'll be used just to connect to a shared database for listing databases 
#                       without root permissions and therefore speed up the queries.
#----------------------------------------------------------
conf['webfaction'] = True   # Put False here if you're not using Odoo in a webfaction environment
conf['webfaction_url'] = 'https://api.webfaction.com/'
conf['webfaction_user'] = ''        # webfaction login user or user created for that purpose
conf['webfaction_password'] = ''    # webfaction user password
conf['webfaction_db_base'] = 'base931562'   # you can put here any db name but it has to be differnet than "conf['db_user']"


#----------------------------------------------------------
# Alternate Logging just for debug
#----------------------------------------------------------
LOG_FILENAME = None #'/home/nuobit/logs/user/odoo.log'

if LOG_FILENAME is not None:
    import logging
    import logging.handlers
    import logging.config

    LOG_CONFIG = {
        'version': 1,              
        'disable_existing_loggers': False,  # this fixes the problem
        'formatters': {
            'detailed': {
                'format': '%(asctime)s - %(filename)s (%(process)d) - %(levelname)s - %(message)s'
            },
            'devel': {
                'format': '%(asctime)s - %(pathname)s:%(lineno)d (%(funcName)s) - %(levelname)s - %(message)s'
            },
            'briefed': {
                'format': '%(asctime)s - %(message)s'
            }
        },
        'handlers': {
            'stderr': {
                'class':'logging.StreamHandler',
                'formatter': 'detailed',
                'level':'DEBUG',    
            },
            'stdout': {
                'class':'logging.StreamHandler',
                'formatter': 'detailed',
                'level':'DEBUG',    
            },
            'file_log': {
                'class': 'logging.handlers.RotatingFileHandler',
                'maxBytes': 10485760,
                'backupCount': 5,
                'filename': LOG_FILENAME,
                'mode': 'a',
                'formatter': 'devel',
                'level':'DEBUG',
            },
        },
        'loggers': {
            '': {                  
                'handlers': ['file_log'],        
                'level': 'DEBUG',  
            'propagate': True  
            }
        }
    }

    logging.config.dictConfig(LOG_CONFIG)

# Gunicorn
#----------------------------------------------------------
# Standard OpenERP XML-RPC port is 8069
bind = '127.0.0.1:8069'
pidfile = '.gunicorn.pid'
workers = 4
timeout = 240
max_requests = 2000

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
