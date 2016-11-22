# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2008-2010 Zikzakmedia S.L. (http://zikzakmedia.com)
#                            Jordi Esteve <jesteve@zikzakmedia.com>
#    Copyright (c) 2012-2013, Grupo OPENTIA (<http://opentia.com>)
#                            Dpto. Consultoría <consultoria@opentia.es>
#    Copyright (c) 2013-2015 Serv. Tecnol. Av. (http://www.serviciosbaeza.com)
#                       Pedro M. Baeza <pedro.baeza@serviciosbaeza.com>
#    Copyright (c) 2015 FactorLibre (www.factorlibre.com)
#                       Carlos Liébana <carlos.liebana@factorlibre.com>
#                       Hugo Santos <hugo.santos@factorlibre.com>
#    Copyright (c) 2015 GAFIC consultores (www.gafic.com)
#                       Albert Cabedo <albert@gafic.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
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
    "name": "Spanish Charts of Accounts (PGCE 2008)",
    "version": "5.3.0",
    "author": "Spanish Localization Team",
    "website": 'https://github.com/OCA/l10n-spain',
    "category": "Localization/Account Charts",
    "license": "AGPL-3",
    "depends": ["account", "base_vat", "base_iban"],
    "data": [
        "data/account_type.xml",
        "data/account_chart_template.xml",
        "data/account_account_common.xml",
        "data/account_account_full.xml",
        "data/account_account_pymes.xml",
        "data/account_account_assoc.xml",
        "data/tax_codes_common.xml",
        "data/taxes_common.xml",
        "data/fiscal_positions_common.xml",
        "data/account_chart_template_post.xml",
        "data/l10n_es_wizard.xml",
    ],
    "installable": True,
    'images': [
        'images/config_chart_l10n_es.png',
        'images/l10n_es_chart.png'
    ],
}
