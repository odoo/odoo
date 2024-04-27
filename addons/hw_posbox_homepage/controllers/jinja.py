
from platform import system

import jinja2
import json
import os
import sys

if hasattr(sys, 'frozen'):
    # When running on compiled windows binary, we don't have access to package loader.
    path = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'views'))
    loader = jinja2.FileSystemLoader(path)
else:
    loader = jinja2.PackageLoader('odoo.addons.hw_posbox_homepage', "views")

jinja_env = jinja2.Environment(loader=loader, autoescape=True)

jinja_env.filters["json"] = json.dumps
jinja_env.globals["iot"] = {
    'is_box': system() == 'Linux',
    'is_virtual': system() == 'Windows',
}
