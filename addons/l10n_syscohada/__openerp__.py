# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2010-2011 BAAMTU SARL (<http://www.baamtu.sn>).
# contact: leadsn@baamtu.com

{
    'name' : 'OHADA - Accounting',
    'version' : '1.0',
    'author' : 'Baamtu Senegal',
    'category' : 'Localization/Account Charts',
    'description': """
This module implements the accounting chart for OHADA area.
===========================================================
    
It allows any company or association to manage its financial accounting.

Countries that use OHADA are the following:
-------------------------------------------
    Benin, Burkina Faso, Cameroon, Central African Republic, Comoros, Congo,
    
    Ivory Coast, Gabon, Guinea, Guinea Bissau, Equatorial Guinea, Mali, Niger,
    
    Replica of Democratic Congo, Senegal, Chad, Togo.
    """,
    'website': 'http://www.baamtu.com',
    'depends' : ['account', 'base_vat'],
    'demo' : [],
    'data' : [
        'l10n_syscohada_data.xml',
        'account_chart_template.yml',
    ],
    'installable': True
}
