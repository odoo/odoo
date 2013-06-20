# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': 'Canada - Accounting',
    'version': '1.1',
    'author': 'Savoir-faire Linux',
    'website': 'http://www.savoirfairelinux.com',
    'category': 'Localization/Account Charts',
    'description': """
This is the module to manage the English and French - Canadian accounting chart in OpenERP.
===========================================================================================

Canadian accounting charts and localizations.
    """,
    'depends': [
        'base',
        'account',
        'base_iban',
        'base_vat',
        'account_chart',
        'account_anglo_saxon'
    ],
    'data': [
        'account_chart_en.xml',
        'account_tax_code_en.xml',
        'account_chart_template_en.xml',
        'account_tax_en.xml',
        'fiscal_templates_en.xml',
        'account_chart_fr.xml',
        'account_tax_code_fr.xml',
        'account_chart_template_fr.xml',
        'account_tax_fr.xml',
        'fiscal_templates_fr.xml',
        'l10n_ca_wizard.xml'
    ],
    'demo': [],
    'installable': True,
    'images': ['images/config_chart_l10n_ca.jpeg','images/l10n_ca_chart.jpeg'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

