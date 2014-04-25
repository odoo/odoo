import sys

# Mock deprecated openerp.addons.web.http module
import openerp.http
sys.modules['openerp.addons.web.http'] = openerp.http
http = openerp.http

import controllers
