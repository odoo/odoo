# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2009-2010 Salvatore Josué Trimarchi Pinto <salvatore@trigluu.com>
# (http://trigluu.com)

#
# This module provides a minimal Honduran chart of accounts that can be use
# to build upon a more complex one.  It also includes a chart of taxes and
# the Lempira currency.
#
# This module is based on the Guatemalan chart of accounts:
# Copyright (c) 2009-2010 Soluciones Tecnologócias Prisma S.A. All Rights Reserved.
# José Rodrigo Fernández Menegazzo, Soluciones Tecnologócias Prisma S.A.
# (http://www.solucionesprisma.com)
#
# This module works with OpenERP 6.0 to 8.0
#

{
    'name': 'Honduras - Accounting',
    'version': '0.1',
    'category': 'Localization/Account Charts',
    'description': """
This is the base module to manage the accounting chart for Honduras.
====================================================================
    
Agrega una nomenclatura contable para Honduras. También incluye impuestos y la
moneda Lempira. -- Adds accounting chart for Honduras. It also includes taxes
and the Lempira currency.""",
    'author': 'Salvatore Josue Trimarchi Pinto',
    'website': 'http://trigluu.com',
    'depends': ['base', 'account'],
    'data': [
        'account_chart.xml',
        'l10n_hn_base.xml',
        'account_chart_template.yml',
    ],
    'demo': [],
    'installable': True,
}
