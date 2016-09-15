# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Author: Nicolas Bessi. Copyright Camptocamp SA
# Financial contributors: Hasa SA, Open Net SA,
#                         Prisme Solutions Informatique SA, Quod SA
# Translation contributors: brain-tec AG, Agile Business Group

{'name': 'Switzerland - Accounting',
 'description':  """
Swiss localization
==================

**Multilang Swiss PME/KMU 2015 account chart and taxes**

**Author:** Camptocamp SA

**Financial contributors:** Prisme Solutions Informatique SA, Quod SA

**Translation contributors:** brain-tec AG, Agile Business Group

The swiss localization addons are organized this way:

``l10n_ch``
  Multilang Swiss PME/KMU 2015 account chart and taxes (official addon)
``l10n_ch_base_bank``
  Technical module that introduces a new and simplified version of bank
  type management
``l10n_ch_bank``
  List of swiss banks
``l10n_ch_zip``
  List of swiss postal zip
``l10n_ch_dta``
  Support of the DTA payment protocol (will be deprecated by the end of 2014)
``l10n_ch_payment_slip``
  Support of ESR/BVR payment slip report and reconciliation.

``l10n_ch`` is located in the core Odoo modules. The other modules are in:
https://github.com/OCA/l10n-switzerland
""",
 'version': '9.0',
 'author': 'Camptocamp',
 'category': 'Localization',
 'website': 'http://www.camptocamp.com',
 'depends': ['account', 'l10n_multilang'],
 'data': ['data/l10n_ch_chart_data.xml',
          'data/account_vat2011_data.xml',
          'data/account_fiscal_position_data.xml',
          'data/account_chart_template_data.yml',

          ],
 'post_init_hook': 'load_translations',
 }
