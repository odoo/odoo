# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# SKR03
# =====

# Dieses Modul bietet Ihnen einen deutschen Kontenplan basierend auf dem SKR03.
# Gemäss der aktuellen Einstellungen ist ein neues Unternehmen in Odoo
# Umsatzsteuerpflichtig. Zahlreiche Erlös- und Aufwandskonten enthalten
# bereits eine zugeordnete Steuer. Hierdurch wird für diese Konten bereits
# die richtige Vorsteuer (Eingangsrechnungen) bzw. Umsatzsteuer
# (Ausgangsrechnungen) automatisch ausgewählt.
#
# Die Zuordnung von Steuerkonten zu Produkten und / oder Sachkonten kann
# für den jeweiligen betrieblichen Anwendungszweck überarbeitet oder
# auch erweitert werden.
# Die mit diesem Kontenrahmen installierten Steuerschlüssel (z.B. 19%, 7%,
# steuerfrei) können hierzu bei den Produktstammdaten hinterlegt werden
# (in Abhängigkeit der Steuervorschriften). Die Zuordnung erfolgt auf
# dem Aktenreiter Finanzbuchhaltung (Kategorie: Umsatzsteuer / Vorsteuer).

# Die Zuordnung der Steuern für Ein- und Ausfuhren aus EU Ländern, sowie auch
# für den Ein- und Verkauf aus und in Drittländer sollten beim Partner
# (Lieferant / Kunde) hinterlegt werden (in Anhängigkeit vom Herkunftsland
# des Lieferanten/Kunden). Diese Zuordnung ist 'höherwertig' als
# die Zuordnung bei Produkten und überschreibt diese im Einzelfall.
#
# Zur Vereinfachung der Steuerausweise und Buchung bei Auslandsgeschäften
# erlaubt Odoo ein generelles Mapping von Steuerausweis und Steuerkonten
# (z.B. Zuordnung 'Umsatzsteuer 19%' zu 'steuerfreie Einfuhren aus der EU')
# zwecks Zuordnung dieses Mappings zum ausländischen Partner (Kunde/Lieferant).


{
    'name': 'Germany SKR03 - Accounting',
    'version': '3.0',
    'author': 'openbig.org',
    'website': 'http://www.openbig.org',
    'category': 'Localization',
    'description': """
Dieses  Modul beinhaltet einen deutschen Kontenrahmen basierend auf dem SKR03.
==============================================================================

German accounting chart and localization.
    """,
    'depends': ['l10n_de'],
    'data': [
        'data/l10n_de_skr03_chart_data.xml',
        'data/account_data.xml',
        'data/account_tax_fiscal_position_data.xml',
        'data/account_reconcile_model_template.xml',
        'data/account_chart_template_data.xml',
    ],
    'auto_install': True
}
