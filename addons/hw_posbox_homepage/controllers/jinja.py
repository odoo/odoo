

import json
import os
import sys

import jinja2

from odoo.http import request
from odoo.addons.hw_drivers.tools.helpers import IS_BOX, IS_VIRTUAL

if hasattr(sys, 'frozen'):
    # When running on compiled windows binary, we don't have access to package loader.
    path = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'views'))
    loader = jinja2.FileSystemLoader(path)
else:
    loader = jinja2.PackageLoader('odoo.addons.hw_posbox_homepage', "views")

jinja_env = jinja2.Environment(loader=loader, autoescape=True)

jinja_env.filters["json"] = json.dumps
jinja_env.globals["iot"] = {
    'IS_BOX': IS_BOX,
    'IS_VIRTUAL': IS_VIRTUAL,
}


def add_jinja_globals(globals_dict: dict):
    """Add global variables to the jinja environment.

    :param globals_dict: the dictionary of global variables to add
    """
    jinja_env.globals["iot"].update(globals_dict)


def render_template(template: str, *context_args, **context_kwargs) -> str:
    """Render a jinja template with the given context.

    e.g. render_template('my_template.jinja2', my_var='value', ...)
         render_template('my_template.jinja2', {'my_var': 'value'}, ...)

    :param template: the template name/path to render
    :param context_args: the positional arguments to pass to the template
    :param context_kwargs: the keyword arguments to pass to the template

    :return: the rendered template
    """
    if template.startswith('technical/'):
        context_kwargs.update({
            'breadcrumb': 'Technical',
            'request_path': request.httprequest.path,
        })
    # Note on performance: jinja environment caches templates
    return jinja_env.get_template(template).render(*context_args, **context_kwargs)
