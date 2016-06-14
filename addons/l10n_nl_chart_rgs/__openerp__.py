# -*- coding: utf-8 -*-
# © 2016 Therp BV (http://therp.nl).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    'name' : 'Netherlands - Accounting - Reference Accounting Scheme (RGS)',
    'version' : '8.0.0.1.0',
    'category': 'Localization/Account Charts',
    'license': 'AGPL-3',                                                          
    'author': 'Odoo Community Association (OCA), Therp BV',                       
    'website': 'https://github.com/OCA/l10n-netherlands',
    'website' : 'http://therp.nl',
    'depends' : [
        'account',
    ],
    'data' : [
        'data/account_account_template.xml',
        'data/account_chart_template.xml',
        'data/account_fiscal_position_template.xml',
        'data/account_fiscal_position_account_template.xml',
        'data/account_tax_template.xml',
        'data/account_fiscal_position_tax_template.xml',
    ],
}
