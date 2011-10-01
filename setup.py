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
from os.path import join, isfile

execfile(join(os.path.dirname(__file__), 'openerp', 'release.py'))

py2exe_keywords = {}
if os.name == 'nt':
    import py2exe
    py2exe_keywords['console'] = [
        { "script": "openerp-server",
          "icon_resources": [(1, join("pixmaps","openerp-icon.ico"))],
        }]
    py2exe_keywords['options'] = {
        "py2exe": {
            "skip_archive": 1,
            "optimize": 2,
            "dist_dir": 'dist',
            "packages": [
                "lxml", "lxml.builder", "lxml._elementpath", "lxml.etree",
                "lxml.objectify", "decimal", "xml", "xml", "xml.dom", "xml.xpath",
                "encodings", "dateutil", "pychart", "PIL", "pyparsing",
                "pydot", "asyncore","asynchat", "reportlab", "vobject",
                "HTMLParser", "select", "mako", "poplib",
                "imaplib", "smtplib", "email", "yaml", "DAV",
                "uuid", "commands", "openerp", "simplejson", "vatnumber"
            ],
            "excludes" : ["Tkconstants","Tkinter","tcl"],
        }
    }

# List all data files
def data():
    files = []
    for root, dirnames, filenames in os.walk('openerp'):
        for filename in filenames:
            if not re.match(r'.*(\.pyc|\.pyo|\~)$',filename):
                files.append(os.path.join(root, filename))
    d = {}
    for v in files:
        k=os.path.dirname(v)
        if k in d:
            d[k].append(v)
        else:
            d[k]=[v]
    r = d.items()
    return r

def gen_manifest():
    file_list="\n".join(data())
    open('MANIFEST','w').write(file_list)

setuptools.setup(
      name             = name,
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
      #include_package_data = True,
      install_requires = [
       # We require the same version as caldav for lxml.
          'lxml==2.1.5',
          'mako',
          'python-dateutil',
          'psycopg2',
        # TODO the pychart package we include in openerp corresponds to PyChart 1.37.
        # It seems there is a single difference, which is a spurious print in generate_docs.py.
        # It is probably safe to move to PyChart 1.39 (the latest one).
        # (Let setup.py choose the latest one, and we should check we can remove pychart from
        # our tree.)
        # http://download.gna.org/pychart/
          'pychart',
          'pydot',
          'pytz',
          'reportlab',
          'caldav',
          'pyyaml',
          'pywebdav',
          'feedparser',
          'simplejson >= 2.0',
          'vatnumber', # required by base_vat module
      ],
      extras_require = {
          'SSL' : ['pyopenssl'],
      },
      **py2exe_keywords
)

