#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2009-2010 Soluciones Tecnologócias Prisma S.A. All Rights Reserved.
# José Rodrigo Fernández Menegazzo, Soluciones Tecnologócias Prisma S.A.
# (http://www.solucionesprisma.com)

#
# This module provides a minimal Guatemalan chart of accounts that can be use
# to build upon a more complex one.  It also includes a chart of taxes and
# the Quetzal currency.
#
# This module is based on the UK minimal chart of accounts:
# Copyright (c) 2004-2009 Seath Solutions Ltd. All Rights Reserved.
# Geoff Gardiner, Seath Solutions Ltd (http://www.seathsolutions.com/)
#
# This module works with OpenERP 6.0
#

{
    'name': 'Guatemala - Accounting',
    'version': '3.0',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
This is the base module to manage the accounting chart for Guatemala.
=====================================================================

Agrega una nomenclatura contable para Guatemala. También icluye impuestos y
la moneda del Quetzal. -- Adds accounting chart for Guatemala. It also includes
taxes and the Quetzal currency.""",
    'author': 'José Rodrigo Fernández Menegazzo',
    'website': 'http://solucionesprisma.com/',
    'depends': ['base', 'account'],
    'data': [
        'data/l10n_gt_chart_data.xml',
        'data/account.account.template.csv',
        'data/l10n_gt_chart_post_data.xml',
        'data/account_data.xml',
        'data/account_chart_template_data.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
}
