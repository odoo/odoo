# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
    'name': 'Turkey - Accounting',
    'version': '1.beta',
    'category': 'Localization/Account Charts',
    'description': """
Türkiye için Tek düzen hesap planı şablonu OpenERP Modülü.
==========================================================

Bu modül kurulduktan sonra, Muhasebe yapılandırma sihirbazı çalışır
    * Sihirbaz sizden hesap planı şablonu, planın kurulacağı şirket, banka hesap
      bilgileriniz, ilgili para birimi gibi bilgiler isteyecek.
    """,
    'author': 'Ahmet Altınışık',
    'maintainer':'https://launchpad.net/~openerp-turkey',
    'website':'https://launchpad.net/openerp-turkey',
    'depends': [
        'account',
        'base_vat',
        'account_chart',
    ],
    'data': [
        'account_code_template.xml',
        'account_tdhp_turkey.xml',
        'account_tax_code_template.xml',
        'account_chart_template.xml',
        'account_tax_template.xml',
        'l10n_tr_wizard.xml',
        ],
    'demo': [],
    'installable': True,
    'images': ['images/chart_l10n_tr_1.jpg','images/chart_l10n_tr_2.jpg','images/chart_l10n_tr_3.jpg'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
