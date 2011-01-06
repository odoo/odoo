# -*- coding: utf-8 -*-
#
#  __terp__.py
#  l10n_ch
#
#  Created by Nicolas Bessi based on Credric Krier contribution
#
#  Copyright (c) 2009 CamptoCamp. All rights reserved.
##############################################################################
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
    "name" : "Switzerland localisation corrected by Camptocamp",
    "description" : """
Swiss localisation :
 - DTA generation for a lot of payment types
 - BVR management (number generation, report, etc..)
 - Import account move from the bank file (like v11 etc..)
 - Simplify the way you handle the bank statement for reconciliation
 - Swiws account chart that add also tax template definition

------------------------------------------------------------------------

Module incluant la localisation Suisse de TinyERP revu et corrigé par Camptocamp. Cette nouvelle version
comprend la gestion et l'émissionde BVR, le paiement électronique via DTA (pour les banques, le système postal est en développement),
l'import du relevé de compte depuis la banque de manière automatisée, le plan de compte Swiws.
De plus, nous avons intégré la définition de toutes les banques Suisses(adresse, swift et clearing).

--------------------------------------------------------------------------
TODO :
- Implement bvr import partial reconciliation
- Replace wizard by osv_memory when possible
- Add mising HELP
- Finish code comment
- Improve demo data


""",
    "version" : "5.1",
    "author" : "Camptocamp SA",
    "category" : "Localisation/Account Charts",
    "website": "http://www.camptocamp.com",

    "depends" : [
        "base_vat",
        "base_iban",
        "account_payment",
        "account_voucher",
        "account",
        "account_chart",
    ],
    "init_xml" : [
        "dta_data.xml",
        "vaudtax_data.xml",
        'account.xml',
        'vat.xml',
    ],
    "demo_xml" : [
        "demo/vaudtax_data_demo.xml",
    ],
    "update_xml" : [
        "dta_view.xml",
        "wizard/bvr_import_view.xml",
        "wizard/bvr_report_view.xml",
        "wizard/create_dta_view.xml",
        "company_view.xml",
        "account_invoice.xml",
        "bank_view.xml",
        'wizard.xml',
        'security/ir.model.access.csv',
    ],
    'test' : [
        'test/l10n_ch_report.yml',
    ],
    "active": False,
    "installable": True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
