import imghdr
import json
import functools
import io
import odoo
import os
import sys
import jinja2
import base64
from odoo import http, tools
from odoo.addons.web.controllers.main import Database, Binary
from odoo.addons.web.controllers import main

if hasattr(sys, 'frozen'):
    # When running on compiled windows binary,
    #  we don't have access to package loader.
    path = \
        os.path.realpath(os.path.join(os.path.dirname(__file__),
                                      '..', 'views'))
    loader = jinja2.FileSystemLoader(path)
else:
    loader = jinja2.PackageLoader('odoo.addons.website_favcion_debrand', "views")
env = main.jinja2.Environment(loader=loader, autoescape=True)
env.filters["json"] = json.dumps
db_monodb = http.db_monodb




class OdooDebrand(Database):
    # Render the Database management html page
    def _render_template(self, **d):
        d.setdefault('manage', True)
        d['insecure'] = odoo.tools.config.verify_admin_password('admin')
        d['list_db'] = odoo.tools.config['list_db']
        d['langs'] = odoo.service.db.exp_list_lang()
        d['countries'] = odoo.service.db.exp_list_countries()
        d['pattern'] = main.DBNAME_PATTERN
        # databases list
        d['databases'] = []
        try:
            d['databases'] = http.db_list()
            d['incompatible_databases'] = \
                odoo.service.db.list_db_incompatible(d['databases'])
        except odoo.exceptions.AccessDenied:
            monodb = db_monodb()
            if monodb:
                d['databases'] = [monodb]

        try:
            d['company_name'] = ''
            d['favicon_url'] = ''
            d['company_logo_url'] = ''
            return env.get_template("database_manager_extend.html").render(d)
        except Exception as e:
            d['company_name'] = ''
            d['favicon_url'] = ''
            d['company_logo_url'] = ''
            return main.env.get_template("database_manager.html").render(d)
