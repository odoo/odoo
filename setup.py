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

import os, setuptools, sys
from os.path import join

if os.name == 'nt':
    sys.path.append("C:\Microsoft.VC90.CRT")


def py2exe_options():
    if os.name == 'nt':
        import py2exe
        return {
            "console" : [ { "script": "openerp-server", "icon_resources": [(1, join("install","openerp-icon.ico"))], },
                          { "script": "openerp-gevent" },
                          { "script": "odoo.py" },
            ],
            'options' : {
                "py2exe": {
                    "skip_archive": 1,
                    "optimize": 0, # keep the assert running, because the integrated tests rely on them.
                    "dist_dir": 'dist',
                    "packages": [
                        "HTMLParser",
                        "PIL",
                        "asynchat", "asyncore",
                        "commands",
                        "dateutil",
                        "decimal",
                        "decorator",
                        "docutils",
                        "email",
                        "encodings",
                        "imaplib",
                        "jinja2",
                        "lxml", "lxml._elementpath", "lxml.builder", "lxml.etree", "lxml.objectify",
                        "mako",
                        "markupsafe",   # dependence of jinja2 and mako
                        "mock",
                        "openerp",
                        "passlib",
                        "poplib",
                        "psutil",
                        "pychart",
                        "pydot",
                        "pyparsing",
                        "pytz",
                        "reportlab",
                        "requests",
                        "select",
                        "simplejson",
                        "smtplib",
                        "uuid",
                        "vatnumber",
                        "vobject",
                        "win32service", "win32serviceutil",
                        "xlwt",
                        "xml", "xml.dom",
                        "yaml",
                    ],
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
      scripts          = ['openerp-server', 'openerp-gevent', 'odoo.py'],
      packages         = setuptools.find_packages() + ['addons.' + i for i in setuptools.find_packages('addons')],
      dependency_links = ['http://download.gna.org/pychart/'],
      include_package_data = True,
      install_requires = [
          'pychart', # not on pypi, use: pip install http://download.gna.org/pychart/PyChart-1.39.tar.gz
          'babel >= 1.0',
          'decorator',
          'docutils',
          'feedparser',
          'gdata',
          'gevent',
          'psycogreen',
          'Jinja2',
          'lxml', # windows binary http://www.lfd.uci.edu/~gohlke/pythonlibs/
          'mako',
          'mock',
          'passlib',
          'pillow', # windows binary http://www.lfd.uci.edu/~gohlke/pythonlibs/
          'psutil', # windows binary code.google.com/p/psutil/downloads/list
          'psycopg2 >= 2.2',
          'pydot',
          'pyparsing < 2',
          'pyserial',
          'python-dateutil < 2',
          'python-ldap', # optional
          'python-openid',
          'pytz',
          'pyusb >= 1.0.0b1',
          'pyyaml',
          'qrcode',
          'reportlab', # windows binary pypi.python.org/pypi/reportlab
          'requests',
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
      tests_require = ['unittest2', 'mock'],
      **py2exe_options()
)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
