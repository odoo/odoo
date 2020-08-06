# -*- coding: utf-8 -*-
import os
import re
import jinja2
import odoo


env = jinja2.Environment()

def snake(s):
    """ snake-casify the given string """
    # insert a space before each uppercase character preceded by a
    # non-uppercase letter
    s = re.sub(r'(?<=[^A-Z])\B([A-Z])', r' \1', s)
    # lowercase everything, split on whitespace and join
    return '_'.join(s.lower().split())

def pascal(s):
    """ pascal-casify the given string """
    return ''.join(
        ss.capitalize()
        for ss in re.sub(r'[_\s]+', ' ', s).split()
    )

env.filters['snake'] = snake
env.filters['pascal'] = pascal


def files(path):
    """
    Lists the (local) path and content of all files in the template
    """
    for root, _, files in os.walk(path):
        for f in files:
            path = os.path.join(root, f)
            with open(path, 'rb') as fd:
                yield path, fd.read()
    

def render(template, modname, directory, params=None):
    """
    Render this module template to ``dest`` with the provided rendering
    parameters
    """
    # overwrite with local
    for path, content in files(template):
        local = os.path.relpath(path, template)
        # strip .template extension
        root, ext = os.path.splitext(local)
        if ext == '.template':
            local = root
        dest = os.path.join(directory, modname, local)
        destdir = os.path.dirname(dest)
        if not os.path.exists(destdir):
            os.makedirs(destdir)

        with open(dest, 'wb') as f:
            if ext not in ('.py', '.xml', '.csv', '.js', '.rst', '.html', '.template'):
                f.write(content)
            else:
                env.from_string(content.decode('utf-8'))\
                   .stream(params or {})\
                   .dump(f, encoding='utf-8')


def main():
    render(
        template=odoo.config['scaffold_template'],
        modname=snake(odoo.config['scaffold_modname']),
        directory=odoo.config['scaffold_destdir'],
        params={
            'name': odoo.config['scaffold_modname']
        },
    )
