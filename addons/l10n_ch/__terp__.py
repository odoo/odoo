# -*- encoding: utf-8 -*-
#
#  __terp__.py
#  l10n_ch
#
#  Created by Nicolas Bessi based on Credric Krier contribution
#
#  Copyright (c) 2010 CamptoCamp. All rights reserved.
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
 - DTA generation for a lot of paiment types
 - BVR management (number generation, report, etc..)
 - Import account move from the bank file (like v11 etc..)
 - Simplify the way you handle the bank statement for reconciliation

You can also add with this module one of the following account plan:
 - l10n_ch_c2c_pcg


    
------------------------------------------------------------------------
    
Module incluant la localisation Suisse de OpenERP revu et corrigé par Camptocamp. Cette nouvelle version 
comprend la gestion et l'émissionde BVR, le paiement électronique via DTA (pour les banques, le système postal est en développement) 
et l'import du relevé de compte depuis la banque de manière automatisée. 
De plus, nous avons intégré la définition de toutes les banques Suisses(adresse, swift et clearing).

Par ailleurs, conjointement à ce module, nous proposons 1 plan comptables issus de l'USAM :


 - l10n_ch_c2c_pcg
 
--------------------------------------------------------------------------
Next features :
- Implement bvr import partial reconciliation
- Replace wizard by osv_memory when possible
- Finish code comment
- Improve demo data
""",
    "version" : "5.0",
    "author" : "Camptocamp SA",
    "category" : "Localisation/Europe",
    "website": "http://www.camptocamp.com",
    
    "depends" : [
        "base", 
        "account", 
        "base_vat", 
        "base_iban",
        "account_payment",
        "account_tax_include", 
    ],
    "init_xml" : [
        "dta_data.xml",
        "data.xml",
    ],
    "demo_xml" : [
      "demo/data_demo.xml",
    ],
    "update_xml" : [
        "dta_view.xml",
        "l10n_ch_wizard.xml",
        "l10n_ch_report.xml",
        "bvr_wizard.xml",
        "bvr_view.xml",
        "company_view.xml",
        "account_invoice.xml",
        "bank_view.xml",
        "account_journal_view.xml",
        "security/ir.model.access.csv",
    ],
    "active": False,
    "installable": True,
}