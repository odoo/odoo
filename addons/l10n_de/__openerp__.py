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
# des Lieferanten/Kunden). Die Zuordnung beim Kunden ist "höherwertig" als
# die Zuordnung bei Produkten und überschreibt diese im Einzelfall.
#
# Zur Vereinfachung der Steuerausweise und Buchung bei Auslandsgeschäften
# erlaubt OpenERP ein generelles Mapping von Steuerausweis und Steuerkonten
# (z.B. Zuordnung "Umsatzsteuer 19%" zu "steuerfreie Einfuhren aus der EU")
# zwecks Zuordnung dieses Mappings zum ausländischen Partner (Kunde/Lieferant).

# Die Rechnungsbuchung beim Einkauf bewirkt folgendes:
# Die Steuerbemessungsgrundlage (exklusive Steuer) wird ausgewiesen bei den
# jeweiligen Kategorien für den Vorsteuer Steuermessbetrag (z.B. Vorsteuer
# Steuermessbetrag Voller Steuersatz 19%).
# Der Steuerbetrag erscheint unter der Kategorie "Vorsteuern" (z.B. Vorsteuer
# 19%). Durch multidimensionale Hierachien können verschiedene Positionen
# zusammengefasst werden und dann in Form eines Reports ausgegeben werden.
#
# Die Rechnungsbuchung beim Verkauf bewirkt folgendes:
# Die Steuerbemessungsgrundlage (exklusive Steuer) wird ausgewiesen bei den
# jeweiligen Kategorien für den Umsatzsteuer Steuermessbetrag
# (z.B. Umsatzsteuer Steuermessbetrag Voller Steuersatz 19%).
# Der Steuerbetrag erscheint unter der Kategorie "Umsatzsteuer"
# (z.B. Umsatzsteuer 19%). Durch multidimensionale Hierachien können
# verschiedene Positionen zusammengefasst werden.
# Die zugewiesenen Steuerausweise können auf Ebene der einzelnen
# Rechnung (Eingangs- und Ausgangsrechnung) nachvollzogen werden,
# und dort gegebenenfalls angepasst werden.

# Rechnungsgutschriften führen zu einer Korrektur (Gegenposition)
# der Steuerbuchung, in Form einer spiegelbildlichen Buchung.

# SKR04
# =====

# Dieses Modul bietet Ihnen einen deutschen Kontenplan basierend auf dem SKR04.
# Gemäss der aktuellen Einstellungen ist die Firma nicht Umsatzsteuerpflichtig,
# d.h. im Standard existiert keine Zuordnung von Produkten und Sachkonten zu
# Steuerschlüsseln.
# Diese Grundeinstellung ist sehr einfach zu ändern und bedarf in der Regel
# grundsätzlich eine initiale Zuweisung von Steuerschlüsseln zu Produkten und / oder
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
# (Lieferant/Kunde) hinterlegt werden (in Anhängigkeit vom Herkunftsland
# des Lieferanten/Kunden). Die Zuordnung beim Kunden ist "höherwertig" als
# die Zuordnung bei Produkten und überschreibt diese im Einzelfall.
#
# Zur Vereinfachung der Steuerausweise und Buchung bei Auslandsgeschäften
# erlaubt OpenERP ein generelles Mapping von Steuerausweis und Steuerkonten
# (z.B. Zuordnung "Umsatzsteuer 19%" zu "steuerfreie Einfuhren aus der EU")
# zwecks Zuordnung dieses Mappings zum ausländischen Partner (Kunde/Lieferant).

# Die Rechnungsbuchung beim Einkauf bewirkt folgendes:
# Die Steuerbemessungsgrundlage (exklusive Steuer) wird ausgewiesen bei den
# jeweiligen Kategorien für den Vorsteuer Steuermessbetrag (z.B. Vorsteuer
# Steuermessbetrag Voller Steuersatz 19%).
# Der Steuerbetrag erscheint unter der Kategorie "Vorsteuern" (z.B. Vorsteuer
# 19%). Durch multidimensionale Hierachien können verschiedene Positionen
# zusammengefasst werden und dann in Form eines Reports ausgegeben werden.
#
# Die Rechnungsbuchung beim Verkauf bewirkt folgendes:
# Die Steuerbemessungsgrundlage (exklusive Steuer) wird ausgewiesen bei den
# jeweiligen Kategorien für den Umsatzsteuer Steuermessbetrag
# (z.B. Umsatzsteuer Steuermessbetrag Voller Steuersatz 19%).
# Der Steuerbetrag erscheint unter der Kategorie "Umsatzsteuer"
# (z.B. Umsatzsteuer 19%). Durch multidimensionale Hierachien können
# verschiedene Positionen zusammengefasst werden.
# Die zugewiesenen Steuerausweise können auf Ebene der einzelnen
# Rechnung (Eingangs- und Ausgangsrechnung) nachvollzogen werden,
# und dort gegebenenfalls angepasst werden.

# Rechnungsgutschriften führen zu einer Korrektur (Gegenposition)
# der Steuerbuchung, in Form einer spiegelbildlichen Buchung.


{
    "name" : "Deutschland - SKR03 and SKR04",
    "version" : "1.0",
    "author" : "openbig.org",
    "website" : "http://www.openbig.org",
    "category" : "Finance",
    "description": """
Dieses  Modul beinhaltet einen deutschen Kontenrahmen basierend auf dem SKR03.
==============================================================================

German accounting chart and localization.
    """,
    "depends" : ['base', 'account', 'base_iban', 'base_vat', 'account_chart'],
    "init_xml" : [ ],
    "demo_xml" : [ ],
    "update_xml" : [
        "account_tax_skr03.xml",
        "account_types_skr03.xml",
        "account_chart_skr03.xml",
        "account_chart_template_skr03.xml",
        "account_tax_fiscal_position_skr03.xml",
        "account_tax_skr04.xml",
        "account_types_skr04.xml",
        "account_chart_skr04.xml",
        "account_chart_template_skr04.xml",
        "account_tax_fiscal_position_skr04.xml",
        "l10n_de_wizard.xml",
    ],
    "installable": True,
    "certificate": "00517849017945584893",
    'images': ['images/config_chart_l10n_de.jpeg','images/l10n_de_chart.jpeg'],
}
