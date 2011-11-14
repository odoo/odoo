# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2008 JAILLET Simon - CrysaLEAD - www.crysalead.fr
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################
{
    "name" : "France - Plan Comptable Général",
    "version" : "1.0",
    "author" : "OpenERP SA",
    "website": "http://www.openerp.com",
    "category" : "Localization/Account Charts",
    "description": """
This is the module to manage the accounting chart for France in OpenERP.
========================================================================

Credits: Sistheo Zeekom CrysaLEAD
""",
    "depends" : ['base', 'account', 'account_chart', 'base_vat'],
    "init_xml" : [],
    "update_xml" : [
        "fr_report_demo.xml",
        "plan_comptable_general_demo.xml",
        "l10n_fr_wizard.xml",
        "fr_pcg_taxes_demo.xml",
        "fr_tax_demo.xml",
        "fr_fiscal_templates_demo.xml",
        "security/ir.model.access.csv",
        "wizard/fr_report_bilan_view.xml",
        "wizard/fr_report_compute_resultant_view.xml",

    ],
    "test": ['test/l10n_fr_report.yml'],
    "demo_xml" : [],
    "certificate" : "00435321693876313629",
    "active": False,
    "installable": True,
    'images': ['images/config_chart_l10n_fr.jpeg','images/l10n_fr_chart.jpeg'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

