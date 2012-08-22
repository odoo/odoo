# -*- encoding: utf-8 -*-
##############################################################################
#
#    Author: Nicolas Bessi. Copyright Camptocamp SA
#    Donors: Hasa SA, Open Net SA and Prisme Solutions Informatique SA
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
    'name' : 'Switzerland - Accounting',
    'description' :  """
Swiss localization :
====================
    - DTA generation for a lot of payment types
    - BVR management (number generation, report.)
    - Import account move from the bank file (like v11)
    - Simplify the way you handle the bank statement for reconciliation

You can also add ZIP and bank completion with:
----------------------------------------------
    - l10n_ch_zip
    - l10n_ch_bank
 
 **Author:** Camptocamp SA
 
 **Donors:** Hasa Sàrl, Open Net Sàrl and Prisme Solutions Informatique SA

Module incluant la localisation Suisse de OpenERP revu et corrigé par Camptocamp.
Cette nouvelle version comprend la gestion et l'émissionde BVR, le paiement
électronique via DTA (pour les banques, le système postal est en développement)
et l'import du relevé de compte depuis la banque de manière automatisée. De plus,
nous avons intégré la définition de toutes les banques Suisses(adresse, swift et clearing).

Par ailleurs, conjointement à ce module, nous proposons la complétion NPA:
--------------------------------------------------------------------------
Vous pouvez ajouter la completion des banques et des NPA avec with:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    - l10n_ch_zip
    - l10n_ch_bank
 
 **Auteur:** Camptocamp SA
 
 **Donateurs:** Hasa Sàrl, Open Net Sàrl and Prisme Solutions Informatique SA

TODO :
------
    - Implement bvr import partial reconciliation
    - Replace wizard by osv_memory when possible
    - Add mising HELP
    - Finish code comment
    - Improve demo data

""",
    'version': '6.1',
    'author': 'Camptocamp',
    'category': 'Localization/Account Charts',
    'website': 'http://www.camptocamp.com',

    'depends' : [ 'account_cancel',
               'base_iban',
               'account_payment',
               'account_voucher',
               'report_webkit',
               'l10n_multilang'],

    'data': ['dta_data.xml',
              'journal_data.xml',
              #FR sterchi chart data
              'sterchi_chart/account.xml',
              'sterchi_chart/vat.xml',
              'sterchi_chart/vat2011.xml',
              'sterchi_chart/fiscal_position.xml',
              'wizard.xml',
              'wizard/bvr_import_view.xml',
              'wizard/create_dta_view.xml',
              'company_view.xml',
              'account_invoice.xml',
              'bank_view.xml',
              'security/ir.model.access.csv',
              'report/report_webkit_html_view.xml'],

    'demo': ['demo/demo.xml',
              'demo/dta_demo.xml'],
    'test': ['test/l10n_ch_report.yml',
          'test/l10n_ch_dta.yml',
          #TODO: uncomment the 2 following tests once they are fixed
          #'test/l10n_ch_v11.yml',
          #'test/l10n_ch_v11_part.yml'
         ],

    'auto_install': False,
    'installable': True,
    'certificate': '001103836064567088989',
    'images': ['images/config_chart_l10n_ch.jpeg','images/l10n_ch_chart.jpeg']}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
