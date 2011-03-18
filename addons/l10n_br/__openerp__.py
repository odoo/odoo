# -*- encoding: utf-8 -*-
#################################################################################
#
#    Copyright (C) 2009  Renato Lima - Akretion
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#################################################################################

{
    'name': 'Brazilian Localization',
    'description': """
This is the base module to manage the accounting chart for Brazil in OpenERP.
==============================================================================
    """,
    'category': 'Localisation/Account Charts',
    'author': 'OpenERP Brasil',
    'website': 'http://openerpbrasil.org',
    'version': '0.6',
    'depends': ['account','account_chart'],
    'init_xml': [],
    'update_xml': [
        'data/account.account.type.csv',
        'data/account.tax.code.template.csv',
        'data/account.account.template.csv',
        'data/l10n_br_account_chart_template.xml',
        'data/account_tax_template.xml'
    ],
    'installable': True,
    'certificate' : '001280994939126801405',
    'images': ['images/1_config_chart_l10n_br.jpeg','images/2_l10n_br_chart.jpeg'],
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
