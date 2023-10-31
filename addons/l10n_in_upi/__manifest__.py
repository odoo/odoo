# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Indian - UPI',
    'version': '1.0',
    'description': """
Invoice with UPI QR code
=========================
This module adds QR code in invoice report for UPI payment allowing to make payment via any UPI app.

To print UPI Qr code add UPI id in company and tick "QR Codes" in configuration
  """,
    'category': 'Accounting/Localizations',
    'depends': ['l10n_in'],
    'data': ['views/res_company_views.xml'],
    'license': 'LGPL-3',
    'auto_install': True,
}
