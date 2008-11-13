#!/usr/bin/env python
# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

# setup from TinERP
#   taken from straw http://www.nongnu.org/straw/index.html
#   taken from gnomolicious http://www.nongnu.org/gnomolicious/
#   adapted by Nicolas Évrard <nicoe@altern.org>
#

import imp
import sys
import os
import glob

from stat import ST_MODE

from distutils.core import setup, Command
from distutils.command.install_scripts import install_scripts
from distutils.file_util import copy_file

if os.name == 'nt':
    import py2exe

sys.path.append(os.path.join(os.path.abspath(os.path.dirname(__file__)), "bin"))

opj = os.path.join

execfile(opj('bin', 'release.py'))

# get python short version
py_short_version = '%s.%s' % sys.version_info[:2]

required_modules = [
    ('psycopg', 'PostgreSQL module'),
    ('xml', 'XML Tools for python'),
    ('libxml2', 'libxml2 python bindings'),
    ('libxslt', 'libxslt python bindings')
]

def check_modules():
    ok = True
    for modname, desc in required_modules:
        try:
            exec('import %s' % modname)
        except ImportError:
            ok = False
            print 'Error: python module %s (%s) is required' % (modname, desc)

    if not ok:
        sys.exit(1)

def find_addons():
    for (dp, dn, names) in os.walk(opj('bin', 'addons')):
        for dirpath, dirnames, filenames in os.walk(dp):
            if '__init__.py' in filenames:
                modname = dirpath.replace(os.path.sep, '.')
                yield modname.replace('bin', 'openerp-server', 1)

def data_files():
    '''Build list of data files to be installed'''
    files = []
    if os.name == 'nt':
        os.chdir('bin')
        for (dp,dn,names) in os.walk('addons'):
            files.append((dp, map(lambda x: opj('bin', dp, x), names)))
        for (dp,dn,names) in os.walk('i18n'):
            files.append((dp, map(lambda x: opj('bin', dp, x), names)))
        os.chdir('..')
        for (dp,dn,names) in os.walk('doc'):
            files.append((dp, map(lambda x: opj(dp, x), names)))
    else:
        man_directory = opj('share', 'man')
        files.append((opj(man_directory, 'man1'), ['man/openerp-server.1']))
        files.append((opj(man_directory, 'man5'), ['man/openerp_serverrc.5']))

        doc_directory = opj('share', 'doc', 'openerp-server-%s' % version)
        files.append((doc_directory, [f for f in glob.glob('doc/*') if os.path.isfile(f)]))
        files.append((opj(doc_directory, 'migrate', '3.3.0-3.4.0'), [f for f in glob.glob('doc/migrate/3.3.0-3.4.0/*') if os.path.isfile(f)]))
        files.append((opj(doc_directory, 'migrate', '3.4.0-4.0.0'), [f for f in glob.glob('doc/migrate/3.4.0-4.0.0/*') if os.path.isfile(f)]))

        openerp_site_packages = opj('lib', 'python%s' % py_short_version, 'site-packages', 'openerp-server')

        files.append((opj(openerp_site_packages, 'i18n'), glob.glob('bin/i18n/*')))
        files.append((opj(openerp_site_packages, 'addons', 'custom'),
            glob.glob('bin/addons/custom/*xml') + glob.glob('bin/addons/custom/*rml') + glob.glob('bin/addons/custom/*xsl')))

        for addon in find_addons():
            add_path = addon.replace('.', os.path.sep).replace('openerp-server', 'bin', 1)
            addon_path = opj('lib', 'python%s' % py_short_version, 'site-packages', add_path.replace('bin', 'openerp-server', 1))

            pathfiles = [
                (
                    addon_path, 
                    glob.glob(opj(add_path, '*xml')) + 
                    glob.glob(opj(add_path, '*csv')) + 
                    glob.glob(opj(add_path, '*sql'))
                ),
                (
                    opj(addon_path, 'data'), 
                    glob.glob(opj(add_path, 'data', '*xml'))
                ), 
                (
                    opj(addon_path, 'report'),
                    glob.glob(opj(add_path, 'report', '*xml')) +
                    glob.glob(opj(add_path, 'report', '*rml')) +
                    glob.glob(opj(add_path, 'report', '*sxw')) +
                    glob.glob(opj(add_path, 'report', '*xsl'))
                ),
                (   opj(addon_path, 'security'),
                    glob.glob(opj(add_path, 'security', '*csv')) +
                    glob.glob(opj(add_path, 'security', '*xml'))
                ),
            ]
            files.extend(pathfiles)
    files.append(('.', [('bin/import_xml.rng')]))
    return files

check_modules()

# create startup script
start_script = \
"#!/bin/sh\n\
cd %s/lib/python%s/site-packages/openerp-server\n\
exec %s ./openerp-server.py $@\n" % (sys.prefix, py_short_version, sys.executable)
# write script
f = open('openerp-server', 'w')
f.write(start_script)
f.close()

options = {
    "py2exe": {
        "compressed": 0,
        "optimize": 2, 
        "packages": ["lxml", "lxml.builder", "lxml._elementpath", "lxml.etree", 
                     "lxml.objectify", "decimal", "xml", "xml.dom", "xml.xpath", 
                     "encodings","mx.DateTime","wizard","pychart","PIL", "pyparsing", 
                     "pydot","asyncore","asynchat"],
        "excludes" : ["Tkconstants","Tkinter","tcl"],
    }
}

setup(name             = name,
      version          = version,
      description      = description,
      long_description = long_desc,
      url              = url,
      author           = author,
      author_email     = author_email,
      classifiers      = filter(None, classifiers.split("\n")),
      license          = license,
      data_files       = data_files(),
      scripts          = ['openerp-server'],
      packages         = ['openerp-server', 
                          'openerp-server.addons',
                          'openerp-server.ir',
                          'openerp-server.osv',
                          'openerp-server.ssl',
                          'openerp-server.service', 
                          'openerp-server.tools',
                          'openerp-server.pychart', 
                          'openerp-server.pychart.afm',
                          'openerp-server.report',
                          'openerp-server.report.printscreen',
                          'openerp-server.report.render',
                          'openerp-server.report.render.rml2pdf',
                          'openerp-server.report.render.rml2html',
                          'openerp-server.wizard', 
                          'openerp-server.workflow'] + \
                         list(find_addons()),
      package_dir      = {'openerp-server': 'bin'},
      console = [ 
          { "script" : "bin\\openerp-server.py", 
            "icon_resources" : [
                (1,"pixmaps\\openerp-icon.ico")
            ]
          }
      ],
      options = options,
      )


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

