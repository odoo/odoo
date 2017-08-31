# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# SKR03
# =====

# Dieses Modul bietet Ihnen einen deutschen Kontenplan basierend auf dem SKR03.
# Gemäss der aktuellen Einstellungen ist die Firma nicht Umsatzsteuerpflichtig.
# Diese Grundeinstellung ist sehr einfach zu ändern und bedarf in der Regel
# grundsätzlich eine initiale Zuweisung von Steuerkonten zu Produkten und / oder
# Sachkonten oder zu Partnern.
# Die Umsatzsteuern (voller Steuersatz, reduzierte Steuer und steuerfrei)
# sollten bei den Produktstammdaten hinterlegt werden (in Abhängigkeit der
# Steuervorschriften). Die Zuordnung erfolgt auf dem Aktenreiter Finanzbuchhaltung
# (Kategorie: Umsatzsteuer).
# Die Vorsteuern (voller Steuersatz, reduzierte Steuer und steuerfrei)
# sollten ebenso bei den Produktstammdaten hinterlegt werden (in Abhängigkeit
# der Steuervorschriften). Die Zuordnung erfolgt auf dem Aktenreiter
# Finanzbuchhaltung (Kategorie: Vorsteuer).
# Die Zuordnung der Steuern für Ein- und Ausfuhren aus EU Ländern, sowie auch
# für den Ein- und Verkauf aus und in Drittländer sollten beim Partner
# (Lieferant/Kunde)hinterlegt werden (in Anhängigkeit vom Herkunftsland
# des Lieferanten/Kunden). Die Zuordnung beim Kunden ist 'höherwertig' als
# die Zuordnung bei Produkten und überschreibt diese im Einzelfall.
#
# Zur Vereinfachung der Steuerausweise und Buchung bei Auslandsgeschäften
# erlaubt Odoo ein generelles Mapping von Steuerausweis und Steuerkonten
# (z.B. Zuordnung 'Umsatzsteuer 19%' zu 'steuerfreie Einfuhren aus der EU')
# zwecks Zuordnung dieses Mappings zum ausländischen Partner (Kunde/Lieferant).

# Die Rechnungsbuchung beim Einkauf bewirkt folgendes:
# Die Steuerbemessungsgrundlage (exklusive Steuer) wird ausgewiesen bei den
# jeweiligen Kategorien für den Vorsteuer Steuermessbetrag (z.B. Vorsteuer
# Steuermessbetrag Voller Steuersatz 19%).
# Der Steuerbetrag erscheint unter der Kategorie 'Vorsteuern' (z.B. Vorsteuer
# 19%). Durch multidimensionale Hierachien können verschiedene Positionen
# zusammengefasst werden und dann in Form eines Reports ausgegeben werden.
#
# Die Rechnungsbuchung beim Verkauf bewirkt folgendes:
# Die Steuerbemessungsgrundlage (exklusive Steuer) wird ausgewiesen bei den
# jeweiligen Kategorien für den Umsatzsteuer Steuermessbetrag
# (z.B. Umsatzsteuer Steuermessbetrag Voller Steuersatz 19%).
# Der Steuerbetrag erscheint unter der Kategorie 'Umsatzsteuer'
# (z.B. Umsatzsteuer 19%). Durch multidimensionale Hierachien können
# verschiedene Positionen zusammengefasst werden.
# Die zugewiesenen Steuerausweise können auf Ebene der einzelnen
# Rechnung (Eingangs- und Ausgangsrechnung) nachvollzogen werden,
# und dort gegebenenfalls angepasst werden.

# Rechnungsgutschriften führen zu einer Korrektur (Gegenposition)
# der Steuerbuchung, in Form einer spiegelbildlichen Buchung.


{
    'name': 'Deutschland SKR03 - Accounting',
    'version': '2.0',
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
        'data/account_chart_template_data.yml',
    ],
    'auto_install': True
}
