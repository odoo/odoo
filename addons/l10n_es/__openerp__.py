# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2008-2010 Zikzakmedia S.L. (http://zikzakmedia.com) All Rights Reserved.
#                            Jordi Esteve <jesteve@zikzakmedia.com>
#    Copyright (c) 2012-2013, Grupo OPENTIA (<http://opentia.com>) Registered EU Trademark.
#                            Dpto. Consultoría <consultoria@opentia.es>
#    Copyright (c) 2013 Serv. Tecnol. Avanzados (http://www.serviciosbaeza.com)
#                       Pedro Manuel Baeza <pedro.baeza@serviciosbaeza.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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
    "name" : "Spanish Charts of Accounts (PGCE 2008)",
    "version" : "4.0",
    "author" : "Spanish Localization Team",
    'website' : 'https://launchpad.net/openerp-spain',
    "category" : "Localization/Account Charts",
    "description": """
Spanish charts of accounts (PGCE 2008).
========================================

    * Defines the following chart of account templates:
        * Spanish general chart of accounts 2008
        * Spanish general chart of accounts 2008 for small and medium companies
        * Spanish general chart of accounts 2008 for associations
    * Defines templates for sale and purchase VAT
    * Defines tax code templates
    * Defines fiscal positions for spanish fiscal legislation
""",
    "license" : "AGPL-3",
    "depends" : ["account", "base_vat", "base_iban"],
    "data" : [
        "account_type.xml",
        "account_chart_template.xml",
        "account_account_common.xml",
        "account_account_full.xml",
        "account_account_pymes.xml",
        "account_account_assoc.xml",
        "tax_codes_common.xml",
        "taxes_common.xml",
        "fiscal_templates_common.xml",
        "account_chart_template_post.xml",
        "l10n_es_wizard.xml",
    ],
    "demo" : [],
    'auto_install': False,
    "installable": True,
    'images': ['images/config_chart_l10n_es.png', 'images/l10n_es_chart.png'],
}
