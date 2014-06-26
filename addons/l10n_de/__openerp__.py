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

{
    'name': 'Deutschland - Accounting',
    'version': '1.1',
    'author': 'copado MEDIA UG',
	'website': 'http://www.copado.de',
    'category': 'Localization/Account Charts',
    'description': """
Dieses Modul beinhaltet die deutschen Kontenrahmen SKR03 und SKR04 nach Datev
und den IKR (Industriekontenrahmen).
==============================================================================
	* Letzte Überarbeitung SKR03: Juni 2014
	* Letzte Überarbeitung SKR04: noch offen
	* In Kürze neuer zusätzlicher Kontenrahmen: IKR


English:
German accounting chart and localization (DATEV SKR03 and SKR04).
	* Last change SKR03: Jun 2014
	* Last change SKR04: open
	* New chart will be comming soon: IKR
    """,
    'depends': [
		'base',
		'account',
		'base_iban',
		'base_vat',
		'account_chart'
	],
    'demo': [],
    'data': [
        'account_tax_skr03.xml',
        'account_types_skr03.xml',
        'account_chart_skr03.xml',
        'account_chart_template_skr03.xml',
        'account_tax_fiscal_position_skr03.xml',
        'account_tax_skr04.xml',
        'account_types_skr04.xml',
        'account_chart_skr04.xml',
        'account_chart_template_skr04.xml',
        'account_tax_fiscal_position_skr04.xml',
        #'account_tax_ikr.xml',						=> todo: add new chart-template (Industriekontenrahmen (IKR)) which is also used sometimes in Germany
        #'account_types_ikr.xml', 					=> part of Industriekontenrahmen
        #'account_chart_ikr.xml', 					=> part of Industriekontenrahmen
        #'account_chart_template_ikr.xml',			=> part of Industriekontenrahmen
        #'account_tax_fiscal_position_ikr.xml',		=> part of Industriekontenrahmen
        'l10n_de_wizard.xml',
    ],
    'installable': True,
    'images': ['images/config_chart_l10n_de.jpeg','images/l10n_de_chart.jpeg'],
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
