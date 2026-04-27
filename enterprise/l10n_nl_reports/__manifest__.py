# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2009 Veritos - Jan Verlaan - www.veritos.nl

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
#   record id='btw_code_5b' op negatieve waarde gezet
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
    'name': 'Netherlands - Accounting Reports',
    'version': '1.5',
    'category': 'Accounting/Localizations/Reporting',
    'description': """
Accounting reports for Netherlands
    """,
    'author': 'Veritos - Jan Verlaan',
    'website': 'http://www.veritos.nl',
    'depends': ['l10n_nl', 'account_reports'],
    'data': [
        'data/account_financial_report_profit_loss.xml',
        'data/account_financial_report_profit_loss_tags.xml',
        'data/account_financial_report_balance_sheet.xml',
        'data/account_financial_report_balance_sheet_tags.xml',
        'data/xml_audit_file_3_2.xml',
        'data/tax_report.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'auto_install': ['l10n_nl', 'account_reports'],
    'license': 'OEEL-1',
}
