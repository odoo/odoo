# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2010 kazacube (http://kazacube.com).
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
    "name" : "Maroc - Plan Comptable Général",
    "version" : "1.0",
    "author" : "kazacube",
    "category" : "Localisation/Account Charts",
    "description": """
This is the base module to manage the accounting chart for Maroc.
=================================================================

Ce  Module charge le modèle du plan de comptes standard Marocain et permet de générer les états comptables aux normes marocaines (Bilan, CPC (comptes de produits et charges), balance générale à 6 colonnes, Grand livre cumulatif...). L'intégration comptable a été validé avec l'aide du Cabinet d'expertise comptable Seddik au cours du troisième trimestre 2010""",
    "website": "http://www.kazacube.com",
    "depends" : ["base", "account"],
    "init_xml" : [],
    "update_xml" : [
                    "security/compta_security.xml",
                    "security/ir.model.access.csv",
                    "account_type.xml",
                    "account_pcg_morocco.xml",
                    "l10n_ma_wizard.xml",
                    "l10n_ma_tax.xml",
                    "l10n_ma_journal.xml",

                    ],
    "demo_xml" : [],
    "active": False,
    "installable": True,
    "certificate" : "00599614652359069981",
    'images': ['images/config_chart_l10n_ma.jpeg','images/l10n_ma_chart.jpeg'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

