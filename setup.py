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

# Backports os.walk with followlinks from python 2.6.
# Needed to add all addons files to data_files for Windows packaging.
def walk_followlinks(top, topdown=True, onerror=None, followlinks=False):
    from os.path import join, isdir, islink
    from os import listdir, error

    try:
        names = listdir(top)
    except error, err:
        if onerror is not None:
            onerror(err)
        return

    dirs, nondirs = [], []
    for name in names:
        if isdir(join(top, name)):
            dirs.append(name)
        else:
            nondirs.append(name)

    if topdown:
        yield top, dirs, nondirs
    for name in dirs:
        path = join(top, name)
        if followlinks or not islink(path):
            for x in walk_followlinks(path, topdown, onerror, followlinks):
                yield x
    if not topdown:
        yield top, dirs, nondirs

if sys.version_info < (2, 6):
    os.walk = walk_followlinks

py2exe_keywords = {}
py2exe_data_files = []
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
                "uuid", "commands", "openerp",
            ],
            "excludes" : ["Tkconstants","Tkinter","tcl"],
        }
    }
    # TODO is it still necessary now that we don't use the library.zip file?
    def data_files():
        '''For Windows, we consider all the addons as data files.
           It seems also that package_data below isn't honored by py2exe.'''
        files = []
        os.chdir('openerp')
        for (dp, dn, names) in os.walk('addons'):
            files.append((join('openerp',dp), map(lambda x: join('openerp', dp, x), names)))
        os.chdir('..')
        files.append(('openerp', [join('openerp', 'import_xml.rng'),]))

        # copy pytz/timzeone
        # TODO check if we have to also copy dateutil's timezone data.
        import pytz
        # Make sure the layout of pytz hasn't changed
        assert (pytz.__file__.endswith('__init__.pyc') or
                pytz.__file__.endswith('__init__.py')), pytz.__file__
        pytz_dir = os.path.dirname(pytz.__file__)

        saved_dir = os.getcwd()
        os.chdir(pytz_dir)
        for dp, dn, names in os.walk('zoneinfo'):
            files.append((join('pytz',dp), map(lambda x: join(pytz_dir, dp, x), names)))
        os.chdir(saved_dir)

        return files
    py2exe_data_files = data_files()

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
      ] + py2exe_data_files,
      scripts          = ['openerp-server'],
      packages = find_packages(),
      include_package_data = True,
      package_data = {
          '': ['*.yml', '*.xml', '*.po', '*.pot', '*.csv'],
      },
      dependency_links = ['http://download.gna.org/pychart/'],
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
          'pychart',
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

