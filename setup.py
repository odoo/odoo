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

from distutils.core import setup, Command
from distutils.command.install_scripts import install_scripts
from distutils.file_util import copy_file

from stat import ST_MODE

opj = os.path.join

name = 'tinyerp-server'
version = '4.0.0'

# get python short version
py_short_version = '%s.%s' % sys.version_info[:2]

included_addons = [
    'account', 'account_followup', 'account_tax_include', 'airport', 'audittrail',
    'base','base_partner_relation', 'base_setup', 'crm', 'custom', 'delivery',
    'edi', 'esale_ez', 'esale_joomla', 'esale_osc',
    'hr', 'hr_evaluation', 'hr_expense', 'hr_skill', 'hr_timesheet',
    'hr_timesheet_ical', 'hr_timesheet_invoice', 'hr_timesheet_project',
    'letter', 'marketing', 'mrp', 'network', 'partner_ldap',
    'product','product_electronic', 'product_expiry', 'product_extended',
    'productivity_analysis', 'product_variant', 'profile_accounting',
    'profile_manufacturing', 'profile_service', 'project', 'purchase',
    'purchase_tax_include', 'report_analytic_line', 'report_crm',
    'report_project', 'report_purchase', 'report_sale', 'sale', 'sale_crm',
    'sale_journal', 'sale_rebate', 'sale_tax_include', 'sandwich', 'scrum',
    'stock', 'subscription', 'travel',
    'l10n_be', 'l10n_ca-qc', 'l10n_ch', 'l10n_ch_pcpbl_association',
    'l10n_ch_pcpbl_independant', 'l10n_ch_pcpbl_menage',
    'l10n_ch_pcpbl_plangen', 'l10n_ch_pcpbl_plangensimpl', 'l10n_ch_vat_brut',
    'l10n_ch_vat_forfait', 'l10n_ch_vat_net', 'l10n_fr', 'l10n_se',
    'l10n_simple', 'l10n_chart_at', 'l10n_chart_au', 'l10n_chart_be_frnl',
    'l10n_chart_br', 'l10n_chart_ca_en', 'l10n_chart_ca_fr',
    'l10n_chart_ch_german', 'l10n_chart_cn', 'l10n_chart_cn_traditional',
    'l10n_chart_co', 'l10n_chart_cz', 'l10n_chart_da', 'l10n_chart_de_skr03',
    'l10n_chart_hu', 'l10n_chart_id', 'l10n_chart_it', 'l10n_chart_it_cc2424',
    'l10n_chart_la', 'l10n_chart_nl', 'l10n_chart_nl_standard', 'l10n_chart_no',
    'l10n_chart_pa', 'l10n_chart_pl', 'l10n_chart_sp', 'l10n_chart_sw',
    'l10n_chart_sw_church', 'l10n_chart_sw_food', 'l10n_chart_uk',
    'l10n_chart_us_general', 'l10n_chart_us_manufacturing',
    'l10n_chart_us_service', 'l10n_chart_us_ucoa', 'l10n_chart_us_ucoa_ez',
    'l10n_chart_ve',]

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
    for addon in included_addons:
        path = opj('bin', 'addons', addon)
        for dirpath, dirnames, filenames in os.walk(path):
            if '__init__.py' in filenames:
                modname = dirpath.replace(os.path.sep, '.')
                yield modname.replace('bin', 'tinyerp-server', 1)

def data_files():
    '''Build list of data files to be installed'''
    files = [(opj('share', 'man', 'man1'),
              ['man/tinyerp-server.1']),
             (opj('share', 'man', 'man5'),
              ['man/terp_serverrc.5']),
             (opj('share','doc', 'tinyerp-server-%s' % version), 
              [f for f in glob.glob('doc/*') if os.path.isfile(f)]),
             (opj('lib','python%s' % py_short_version, 'site-package', 'tinyerp-server', 'i18n'), 
              glob.glob('bin/i18n/*')),
             (opj('lib', 'python%s' % py_short_version, 'site-packages', 'tinyerp-server', 'addons', 'custom'),
              glob.glob('bin/addons/custom/*xml') + 
              glob.glob('bin/addons/custom/*rml') +
              glob.glob('bin/addons/custom/*xsl'))]
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

long_desc = '''\
Tiny ERP is a complete ERP and CRM. The main features are accounting (analytic
and financial), stock management, sales and purchases management, tasks
automation, marketing campaigns, help desk, POS, etc. Technical features include
a distributed server, flexible workflows, an object database, a dynamic GUI,
customizable reports, and SOAP and XML-RPC interfaces.
'''

classifiers = """\
Development Status :: 5 - Production/Stable
License :: OSI Approved :: GNU General Public License (GPL)
Programming Language :: Python
"""

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

setup(name             = name,
      version          = version,
      description      = "Tiny's Enterprise Resource Planning",
      long_description = long_desc,
      url              = 'http://tinyerp.com',
      author           = 'Tiny.be',
      author_email     = 'info@tiny.be',
      classifiers      = filter(None, classifiers.split("\n")),
      license          = 'GPL',
      data_files       = data_files(),
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
      scripts          = ['tinyerp-server']
      )

# vim:expandtab:tw=80
