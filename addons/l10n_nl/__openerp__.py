# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2009 Veritos - Jan Verlaan - www.veritos.nl
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs.
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company like Veritos.
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
#
#    Deze module werkt in OpenERP 5.0.0 (en waarschijnlijk hoger).
#    Deze module werkt niet in OpenERP versie 4 en lager.
#
#    Status 1.0 - getest op OpenERP 5.0.3
#
# Versie 5.0.0.1
#   account.account.type
#     Basis gelegd voor alle account type
#
#   account.account.template
#     Basis gelegd met alle benodigde grootboekrekeningen welke via een menu-
#     structuur gelinkt zijn aan rubrieken 1 t/m 9.
#     De grootboekrekeningen gelinkt aan de account.account.type
#     Deze links moeten nog eens goed nagelopen worden.
#
#   account.chart.template
#     Basis gelegd voor het koppelen van rekeningen aan debiteuren, crediteuren,
#     bank, inkoop en verkoop boeken en de BTW configuratie.
#
# Versie 5.0.0.2
#   account.tax.code.template
#     Basis gelegd voor de BTW configuratie (structuur)
#     Heb als basis het BTW aangifte formulier gebruikt. Of dit werkt?
#
#   account.tax.template
#     De BTW rekeningen aangemaakt en deze gekoppeld aan de betreffende
#     grootboekrekeningen
#
# Versie 5.0.0.3
#   Opschonen van de code en verwijderen van niet gebruikte componenten.
# Versie 5.0.0.4
#   Aanpassen a_expense van 3000 -> 7000
#   record id="btw_code_5b" op negatieve waarde gezet
# Versie 5.0.0.5
#   BTW rekeningen hebben typeaanduiding gekregen t.b.v. purchase of sale
# Versie 5.0.0.6
#   Opschonen van module.
# Versie 5.0.0.7
#   Opschonen van module.
# Versie 5.0.0.8
#   Foutje in l10n_nl_wizard.xml gecorrigeerd waardoor de module niet volledig installeerde.
# Versie 5.0.0.9
#   Account Receivable en Payable goed gedefinieerd.
# Versie 5.0.1.0
#   Alle user_type_xxx velden goed gedefinieerd.
#   Specifieke bouw en garage gerelateerde grootboeken verwijderd om een standaard module te creeeren.
#   Deze module kan dan als basis worden gebruikt voor specifieke doelgroep modules te creeeren.
# Versie 5.0.1.1
#   Correctie van rekening 7010 (stond dubbel met 7014 waardoor installatie verkeerd ging)
# versie 5.0.1.2
#   Correctie op diverse rekening types van user_type_asset -> user_type_liability en user_type_equity
# versie 5.0.1.3
#   Kleine correctie op BTW te vorderen hoog, id was hetzelfde voor beide, waardoor hoog werd overschreven door #   overig. Verduidelijking van omschrijvingen in belastingcodes t.b.v. aangifte overzicht.
# versie 5.0.1.4
#   BTW omschrijvingen aangepast, zodat rapporten er beter uitzien. 2a en 5b e.d. verwijderd en enkele omschrijvingen toegevoegd.
# versie 5.0.1.5 - Switch to English
#   Added properties_stock_xxx accounts for correct stock valuation, changed 7000-accounts from type cash to type expense
#   Changed naming of 7020 and 7030 to Kostprijs omzet xxxx

{
    "name" : "Netherlands - Grootboek en BTW rekeningen",
    "version" : "1.5",
    "category": "Localization/Account Charts",
    "description": """
This is the module to manage the accounting chart for Netherlands in OpenERP.
=============================================================================

Read changelog in file __openerp__.py for version information.
Dit is een basismodule om een uitgebreid grootboek- en BTW schema voor Nederlandse bedrijven te installeren in OpenERP versie 5.

De BTW rekeningen zijn waar nodig gekoppeld om de juiste rapportage te genereren, denk b.v. aan intracommunautaire verwervingen
waarbij u 19% BTW moet opvoeren, maar tegelijkertijd ook 19% als voorheffing weer mag aftrekken.

Na installatie van deze module word de configuratie wizard voor "Accounting" aangeroepen.
    * U krijgt een lijst met grootboektemplates aangeboden waarin zich ook het Nederlandse grootboekschema bevind.

    * Als de configuratie wizard start, wordt u gevraagd om de naam van uw bedrijf in te voeren, welke grootboekschema te installeren, uit hoeveel cijfers een grootboekrekening mag bestaan, het rekeningnummer van uw bank en de currency om Journalen te creeren.

Let op!! -> De template van het Nederlandse rekeningschema is opgebouwd uit 4 cijfers. Dit is het minimale aantal welk u moet invullen, u mag het aantal verhogen. De extra cijfers worden dan achter het rekeningnummer aangevult met "nullen"

    * Dit is dezelfe configuratie wizard welke aangeroepen kan worden via Financial Management/Configuration/Financial Accounting/Financial Accounts/Generate Chart of Accounts from a Chart Template.

    """,
    "author"  : "Veritos - Jan Verlaan",
    "website" : "http://www.veritos.nl",
    "depends" : ["account",
                 "base_vat",
                 "base_iban",
                 "account_chart"
                 ],
    "init_xml" : [],
    "update_xml" : ["account_chart_netherlands.xml",
                    "l10n_nl_wizard.xml"
                   ],
    "demo_xml" : [
                 ],

    "installable": True,
    'certificate': '00976041422960053277',
    'images': ['images/config_chart_l10n_nl.jpeg','images/l10n_nl_chart.jpeg'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

