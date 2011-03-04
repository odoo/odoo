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

# setup from TinERP
#   taken from straw http://www.nongnu.org/straw/index.html
#   taken from gnomolicious http://www.nongnu.org/gnomolicious/
#   adapted by Nicolas Évrard <nicoe@altern.org>
#
# doc/migrate is not included since about 6.1-dev
# doc/tests is not included
# python25-compat/*py should be in the openerp (and imported appropriately)

import sys
import os
from os.path import join, isfile
import glob

from setuptools import setup, find_packages

py2exe_keywords = {}
if os.name == 'nt':
    import py2exe
    py2exe_keywords['console'] = [
        { "script": join("bin", "openerp-server.py"),
          "icon_resources": [(1, join("pixmaps","openerp-icon.ico"))],
        }]
    py2exe_keywords['options'] = {
        "py2exe": {
            "compressed": 1,
            "optimize": 2,
            "dist_dir": 'dist',
            "packages": [
                "lxml", "lxml.builder", "lxml._elementpath", "lxml.etree",
                "lxml.objectify", "decimal", "xml", "xml", "xml.dom", "xml.xpath",
                "encodings", "dateutil", "wizard", "pychart", "PIL", "pyparsing",
                "pydot", "asyncore","asynchat", "reportlab", "vobject",
                "HTMLParser", "select", "mako", "poplib",
                "imaplib", "smtplib", "email", "yaml", "DAV",
                "uuid",
            ],
            "excludes" : ["Tkconstants","Tkinter","tcl"],
        }
    }

execfile(join('openerp', 'release.py'))

setup(name             = name,
      version          = version,
      description      = description,
      long_description = long_desc,
      url              = url,
      author           = author,
      author_email     = author_email,
      classifiers      = filter(None, classifiers.split("\n")),
      license          = license,
      data_files       = [
        (join('man', 'man1'), ['man/openerp-server.1']),
        (join('man', 'man5'), ['man/openerp_serverrc.5']),
        ('doc', filter(isfile, glob.glob('doc/*'))),
      ],
      scripts          = ['openerp-server.py'],
      packages = find_packages(),
      include_package_data = True,
      package_data = {
          '': ['*.yml', '*.xml', '*.po', '*.pot', '*.csv'],
      },
      install_requires = [
       # We require the same version as caldav for lxml.
          'lxml==2.1.5',
          'mako',
          'python-dateutil',
          'psycopg2',
        # We include pychart in our tree as it is difficult to get it via pypi.
        # An alternate site is http://home.gna.org/pychart/.
        # 'pychart',
          'pydot',
          'pytz',
          'reportlab',
          'caldav',
          'pyyaml',
          'pywebdav',
          'feedparser',
      ],
      extras_require = {
          'SSL' : ['pyopenssl'],
      },
      **py2exe_keywords
)

