#!/usr/bin/env python
# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import glob, os, re, setuptools, sys
from os.path import join

# List all data files
def data():
    r = {}
    for root, dirnames, filenames in os.walk('openerp'):
        for filename in filenames:
            if not re.match(r'.*(\.pyc|\.pyo|\~)$', filename):
                r.setdefault(root, []).append(os.path.join(root, filename))

    if os.name == 'nt':
        r["Microsoft.VC90.CRT"] = glob.glob('C:\Microsoft.VC90.CRT\*.*')

        import babel
        r["localedata"] = glob.glob(os.path.join(os.path.dirname(babel.__file__), "localedata", '*'))

        import pytz
        tzdir = os.path.dirname(pytz.__file__)
        for root, _, filenames in os.walk(os.path.join(tzdir, "zoneinfo")):
            base = os.path.join('pytz', root[len(tzdir) + 1:])
            r[base] = [os.path.join(root, f) for f in filenames]

        import docutils
        dudir = os.path.dirname(docutils.__file__)
        for root, _, filenames in os.walk(dudir):
            base = os.path.join('docutils', root[len(dudir) + 1:])
            r[base] = [os.path.join(root, f) for f in filenames if not f.endswith(('.py', '.pyc', '.pyo'))]

    return r.items()

def gen_manifest():
    file_list="\n".join(data())
    open('MANIFEST','w').write(file_list)

if os.name == 'nt':
    sys.path.append("C:\Microsoft.VC90.CRT")

def py2exe_options():
    if os.name == 'nt':
        import py2exe
        return {
            "console" : [ { "script": "openerp-server", "icon_resources": [(1, join("install","openerp-icon.ico"))], }],
            'options' : {
                "py2exe": {
                    "skip_archive": 1,
                    "optimize": 2,
                    "dist_dir": 'dist',
                    "packages": [ "DAV", "HTMLParser", "PIL", "asynchat", "asyncore", "commands", "dateutil", "decimal", "docutils", "email", "encodings", "imaplib", "jinja2", "lxml", "lxml._elementpath", "lxml.builder", "lxml.etree", "lxml.objectify", "mako", "openerp", "poplib", "pychart", "pydot", "pyparsing", "pytz", "reportlab", "select", "simplejson", "smtplib", "uuid", "vatnumber", "vobject", "xml", "xml.dom", "yaml", ],
                    "excludes" : ["Tkconstants","Tkinter","tcl"],
                }
            }
        }
    else:
        return {}

execfile(join(os.path.dirname(__file__), 'openerp', 'release.py'))

# Notes for OpenERP developer on windows:
#
# To setup a windows developer evironement install python2.7 then pip and use
# "pip install <depencey>" for every dependency listed below.
#
# Dependecies that requires DLLs are not installable with pip install, for
# them we added comments with links where you can find the installers.
#
# OpenERP on windows also require the pywin32, the binary can be found at
# http://pywin32.sf.net
#
# Both python2.7 32bits and 64bits are known to work.

setuptools.setup(
      name             = 'openerp',
      version          = version,
      description      = description,
      long_description = long_desc,
      url              = url,
      author           = author,
      author_email     = author_email,
      classifiers      = filter(None, classifiers.split("\n")),
      license          = license,
      scripts          = ['openerp-server'],
      data_files       = data(),
      packages         = setuptools.find_packages(),
      dependency_links = ['http://download.gna.org/pychart/'],
      #include_package_data = True,
      install_requires = [
          'pychart', # not on pypi, use: pip install http://download.gna.org/pychart/PyChart-1.39.tar.gz
          'babel',
          'docutils',
          'feedparser',
          'gdata',
          'Jinja2',
          'lxml', # windows binary http://www.lfd.uci.edu/~gohlke/pythonlibs/
          'mako',
          'mock',
          'PIL', # windows binary http://www.lfd.uci.edu/~gohlke/pythonlibs/
          'psutil', # windows binary code.google.com/p/psutil/downloads/list
          'psycopg2 >= 2.2',
          'pydot',
          'python-dateutil < 2',
          'python-ldap', # optional
          'python-openid',
          'pytz',
          'pywebdav',
          'pyyaml',
          'reportlab', # windows binary pypi.python.org/pypi/reportlab
          'simplejson',
          'unittest2',
          'vatnumber',
          'vobject',
          'werkzeug',
          'xlwt',
      ],
      extras_require = {
          'SSL' : ['pyopenssl'],
      },
      tests_require = ['unittest2'],
      **py2exe_options()
)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
