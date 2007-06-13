#!/usr/bin/env python
# -*- coding: utf-8 -*-
# setup from TinERP
#   taken from straw http://www.nongnu.org/straw/index.html
#   taken from gnomolicious http://www.nongnu.org/gnomolicious/
#   adapted by Nicolas Évrard <nicoe@altern.org>
#
# $Id$

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

required_modules = [('psycopg', 'PostgreSQL module'),
                    ('xml', 'XML Tools for python'),
                    ('libxml2', 'libxml2 python bindings'),
                    ('libxslt', 'libxslt python bindings')]

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
        if '.svn' in dn:
            dn.remove('.svn')
        for dirpath, dirnames, filenames in os.walk(dp):
            if '__init__.py' in filenames:
                modname = dirpath.replace(os.path.sep, '.')
                yield modname.replace('bin', 'tinyerp-server', 1)

def data_files():
    '''Build list of data files to be installed'''
    files = []
    if os.name == 'nt':
        os.chdir('bin')
        for (dp,dn,names) in os.walk('addons'):
            if '.svn' in dn:
                dn.remove('.svn')
            files.append((dp, map(lambda x: os.path.join('bin', dp,x), names)))
        for (dp,dn,names) in os.walk('i18n'):
            if '.svn' in dn:
                dn.remove('.svn')
            files.append((dp, map(lambda x: os.path.join('bin', dp,x), names)))
        os.chdir('..')
        for (dp,dn,names) in os.walk('doc'):
            if '.svn' in dn:
                dn.remove('.svn')
            files.append((dp, map(lambda x: os.path.join(dp,x), names)))
    else:
        files.append((opj('share', 'man', 'man1'), ['man/tinyerp-server.1']))
        files.append((opj('share', 'man', 'man5'), ['man/terp_serverrc.5']))
        files.append((opj('share','doc', 'tinyerp-server-%s' % version), [f for
            f in glob.glob('doc/*') if os.path.isfile(f)]))
        files.append((opj('share','doc', 'tinyerp-server-%s' % version,
            'migrate', '3.3.0-3.4.0'), [f for f in
                glob.glob('doc/migrate/3.3.0-3.4.0/*') if os.path.isfile(f)]))
        files.append((opj('share','doc', 'tinyerp-server-%s' % version,
            'migrate', '3.4.0-4.0.0'), [f for f in
                glob.glob('doc/migrate/3.4.0-4.0.0/*') if os.path.isfile(f)]))
        files.append((opj('lib','python%s' % py_short_version, 'site-packages',
            'tinyerp-server', 'i18n'), glob.glob('bin/i18n/*')))
        files.append((opj('lib', 'python%s' % py_short_version, 'site-packages',
            'tinyerp-server', 'addons', 'custom'),
            glob.glob('bin/addons/custom/*xml') +
            glob.glob('bin/addons/custom/*rml') +
            glob.glob('bin/addons/custom/*xsl')))
        for addon in find_addons():
            add_path = addon.replace('.', os.path.sep).replace('tinyerp-server', 'bin',
                                                               1)
            pathfiles = [(opj('lib', 'python%s' % py_short_version, 'site-packages', 
                              add_path.replace('bin', 'tinyerp-server', 1)),
                          glob.glob(opj(add_path, '*xml')) +
                          glob.glob(opj(add_path, '*csv')) +
                          glob.glob(opj(add_path, '*sql'))),
                         (opj('lib', 'python%s' % py_short_version, 'site-packages',
                              add_path.replace('bin', 'tinyerp-server', 1), 'data'),
                          glob.glob(opj(add_path, 'data', '*xml'))), 
                         (opj('lib', 'python%s' % py_short_version, 'site-packages',
                              add_path.replace('bin', 'tinyerp-server', 1), 'report'),
                          glob.glob(opj(add_path, 'report', '*xml')) +
                          glob.glob(opj(add_path, 'report', '*rml')) +
                          glob.glob(opj(add_path, 'report', '*xsl')))]
            files.extend(pathfiles)
    return files

check_modules()

# create startup script
start_script = \
"#!/bin/sh\n\
cd %s/lib/python%s/site-packages/tinyerp-server\n\
exec %s ./tinyerp-server.py $@" % (sys.prefix, py_short_version, sys.executable)
# write script
f = open('tinyerp-server', 'w')
f.write(start_script)
f.close()

options = {"py2exe": {
    "compressed": 0,
    "optimize": 2, 
    "packages": ["encodings","mx.DateTime","wizard","pychart","PIL", "pyparsing", "pydot"],
    "excludes" : ["Tkconstants","Tkinter","tcl"],
    }}

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
      scripts          = ['tinyerp-server'],
      packages         = ['tinyerp-server', 'tinyerp-server.addons',
                          'tinyerp-server.ir',
                          'tinyerp-server.osv',
                          'tinyerp-server.ssl',
                          'tinyerp-server.service', 'tinyerp-server.tools',
                          'tinyerp-server.pychart', 'tinyerp-server.pychart.afm',
                          'tinyerp-server.report',
                          'tinyerp-server.report.printscreen',
                          'tinyerp-server.report.render',
                          'tinyerp-server.report.render.rml2pdf',
                          'tinyerp-server.report.render.rml2html',
                          'tinyerp-server.wizard', 'tinyerp-server.workflow'] + \
                         list(find_addons()),
      package_dir      = {'tinyerp-server': 'bin'},
      console = [{"script":"bin\\tinyerp-server.py", "icon_resources":[(1,"pixmaps\\tinyerp.ico")]}],
      options = options,
      )

# vim:expandtab:tw=80
