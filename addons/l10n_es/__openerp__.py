# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2008-2010 Zikzakmedia S.L. (http://zikzakmedia.com) All Rights Reserved.
#                         Jordi Esteve <jesteve@zikzakmedia.com>
# Copyright (c) 2012-2013, Grupo OPENTIA (<http://opentia.com>) Registered EU Trademark.
#                         Dpto. Consultoría <consultoria@opentia.es>
# Copyright (c) 2013 Serv. Tecnol. Avanzados (http://www.serviciosbaeza.com)
#                    Pedro Manuel Baeza <pedro.baeza@serviciosbaeza.com>

{
    "name" : "Spain - Accounting (PGCE 2008)",
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
    "depends" : ["account", "base_vat", "base_iban"],
    "data" : [
        "account_type.xml",
        "account_chart_template.xml",
        "account_account_common.xml",
        "taxes_common.xml",
        "fiscal_templates_common.xml",
        "account_chart_template_post.xml",
        "account_chart_template.yml",
    ],
    "demo" : [],
    'auto_install': False,
    "installable": True,
    'images': ['images/config_chart_l10n_es.png', 'images/l10n_es_chart.png'],
}
