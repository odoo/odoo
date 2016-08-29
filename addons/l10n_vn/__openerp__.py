# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# This module is Copyright (c) 2009-2013 General Solutions (http://gscom.vn) All Rights Reserved.

{
    "name" : "Vietnam - Accounting",
    "author" : "General Solutions",
    'website': 'http://gscom.vn',
    'category': 'Localization',
    "description": """
This is the module to manage the accounting chart for Vietnam in Odoo.
=========================================================================

This module applies to companies based in Vietnamese Accounting Standard (VAS).

**Credits:** General Solutions.
""",
    "depends" : ["account","base_vat","base_iban"],
    "data": ['data/l10n_vn_chart_data.xml',
             'data/account_tax_data.xml',
             'data/account_chart_template_data.yml'],
}
