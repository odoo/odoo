# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2010 karizma (http://karizma.ma).

{
    'name': 'Maroc - Accounting',
    'version': '1.0',
    'author': 'Karizma Conseil',
    'category': 'Localization',
    'description': """
This is the base module to manage the accounting chart for Morocco.
=================================================================

It adds the ICE code to the customer invoices according to the new Moroccan finance law.

Ce Module charge le modèle du plan de comptes standard Marocain et permet de configurer les taxes et les comptes comptables convenablement. 
il permet également d'ajouter l'ICE sur les factures conformément à la nouvelle loi de finance marocaine""",

    'website': 'http://www.karizma.ma',
    'depends': ['account', 'web'],
    'data': [
        'data/l10n_ma_chart_data.xml',
        'data/account_chart_template_data.xml',
        'data/account_tax_data.xml',
        'data/account_chart_template_configure_data.xml',
        'views/partner_view.xml',
        'views/company.xml',
        'reports/invoice_report.xml',
        'reports/footer.xml',
    ],
}
