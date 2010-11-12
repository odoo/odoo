# -*- encoding: utf-8 -*-
##############################################################################
#
#    Italian OpenERP accounting module
#    Copyright (C) 2010 Servabit srl (<http://www.servabit.it>)
#
#    Developed by the servabit OpenERP team: openerp@servabit.it
#
#    Some parts have been taken from modules by the:
#    Italian OpenERP Community (<http://www.openerp-italia.com>)
#    Some files follows the ideas in the l10n_fr module,
#    by JAILLET Simon - CrysaLEAD - www.crysalead.fr
#
#############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
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
##############################################################################

{
    "name": "Italy - Chart of Accounts By Servabit",
    "version": "0.4",
    "author": "Servabit srl",
    "website": "http://www.servabit.it",
    "category": "Localisation/Account Charts",
    "description": """This is a module to manage the accounting chart for Italy (CC2424 Profile) for a service company.""",
    "depends": ["account", "base_iban", "base_vat", "account_chart"],
    "demo_xml": [],
    "update_xml": [
        'tipoconti_servabit.xml',
        'pianoconti_servabit.xml',
        'account_tax_template.xml',
        'journals.xml',
        'default_accounts.xml',
        'anno_fiscale.xml',
        'l10n_chart_it_servabit_wizard.xml',
        'report.xml',
        'libroIVA_view.xml',
        'libroIVA_menu.xml',
        'security/ir.model.access.csv'
    ],
    "active": False,
    "installable": True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: