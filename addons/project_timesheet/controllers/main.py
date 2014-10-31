import jinja2
import os
import simplejson
import sys

from openerp import http

if hasattr(sys, 'frozen'):
    # When running on compiled windows binary, we don't have access to package loader.
    path = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'views'))
    loader = jinja2.FileSystemLoader(path)
else:
    loader = jinja2.PackageLoader('openerp.addons.project_timesheet', "views")

env = jinja2.Environment(loader=loader, autoescape=True)
env.filters["json"] = simplejson.dumps

class Database(http.Controller):
    @http.route('/project_timesheet/project_timesheet_ui', type='http', auth="user")
    def project_timesheet_ui(self, **kw):
        return env.get_template("index.html").render({})