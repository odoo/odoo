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
    "name": "Indian Chart of Account",
    "version": "1.0",
    "description": """
Indian Accounting : Chart of Account.
=====================================

Indian accounting chart and localization.
    """,
    "author": ['OpenERP SA', 'Axelor'],
    "category": "Localisation/Account Charts",
    "depends": [
        "account",
        "account_chart"
    ],
    "demo_xml": [],
    "update_xml": [
        "l10n_in_chart.xml",
        "l10n_in_wizard.xml",
    ],
    "active": False,
    "installable": True,
    "certificate" : "001308250150600713245",
    'images': ['images/config_chart_l10n_in.jpeg','images/l10n_in_chart.jpeg'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
