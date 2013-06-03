# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Nicolas Bessi. Copyright Camptocamp SA
#    Financial contributors: Hasa SA, Open Net SA,
#                            Prisme Solutions Informatique SA, Quod SA
#
#    Translation contributors: brain-tec AG, Agile Business Group
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

{'name': 'Switzerland - Accounting',
 'description':  """
 Swiss localization :
 ====================
 **Multilang swiss STERCHI account chart and taxes**
  **Author:** Camptocamp SA

  **Financial contributors:** Prisme Solutions Informatique SA, Quod SA

  **Translation contributors:** brain-tec AG, Agile Business Group

 **This release will introduce major changes to l10n_ch.**

 Due to important refactoring needs and the Switzerland adoption of new international payment standard during 2013-2014. We have reorganised the swiss localization addons this way:

 - **l10n_ch**: Multilang swiss STERCHI account chart and taxes (official addon)
 - **l10n_ch_base_bank**: Technical module that introduces a new and simplified version of bank type management
 - **l10n_ch_bank**: List of swiss banks
 - **l10n_ch_zip**: List of swiss postal zip
 - **l10n_ch_dta**: Support of dta payment protocol (will be deprecated end 2014)
 - **l10n_ch_payment_slip**: Support of ESR/BVR payment slip report and reconciliation. Report refactored with easy element positioning.
 - **l10n_ch_sepa**: Alpha implementation of PostFinance SEPA/PAIN support will be completed during 2013/2014

 The modules will be soon available on OpenERP swiss localization on launchpad:
 https://launchpad.net/openerp-swiss-localization
""",
 'version': '7.0',
 'author': 'Camptocamp',
 'category': 'Localization/Account Charts',
 'website': 'http://www.camptocamp.com',
 'depends': ['account', 'l10n_multilang'],
 'data': ['sterchi_chart/account.xml',
          'sterchi_chart/vat2011.xml',
          'sterchi_chart/fiscal_position.xml' ],
 'demo': [],
 'test': [],
 'auto_install': False,
 'installable': True,
 'images': ['images/config_chart_l10n_ch.jpeg','images/l10n_ch_chart.jpeg']
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
