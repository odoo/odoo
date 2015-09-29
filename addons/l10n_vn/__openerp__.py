# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# This module is Copyright (c) 2009-2013 General Solutions (http://gscom.vn) All Rights Reserved.

{
    "name" : "Vietnam - Accounting",
    "version" : "1.0",
    "author" : "General Solutions",
    'website': 'http://gscom.vn',
    "category" : "Localization/Account Charts",
    "description": """
This is the module to manage the accounting chart for Vietnam in OpenERP.
=========================================================================

This module applies to companies based in Vietnamese Accounting Standard (VAS).

**Credits:** General Solutions.
""",
    "depends" : ["account","base_vat","base_iban"],
    "data" : ["account_chart.xml","account_tax.xml","account_chart_template.yml"],
    "demo" : [],
    "installable": True,
}
