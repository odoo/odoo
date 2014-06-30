# -*- encoding: utf-8 -*-
##############################################################################
#
#     Author: Tatár Attila <atta@nvm.ro>, Fekete Mihai <feketemihai@gmail.com>
#    Copyright (C) 2011-2014 TOTAL PC SYSTEMS (http://www.erpsystems.ro).
#    Copyright (C) 2014 Fekete Mihai
#    Copyright (C) 2014 Tatár Attila
#     Based on precedent versions developed by Fil System, Fekete Mihai
#     
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    "name" : "Romania - Accounting",
    "version" : "3.0",
    "author" : "TOTAL PC Systems",
    "website": "http://www.erpsystems.ro",
    "category" : "Localization/Account Charts",
    "depends" : ['account',
                 'account_chart',
                 'base_vat',
    ],
    "description": """
Localization - Accounting base for Romania
-------------------------------------------

Main features include:
    - Accounting chart, taxes
    - VAT structure 
    - Registration Number from Chamber of Commerce and Industry
    - Several initial settings

    **~*~**
Modulul conţine planul de conturi, cote TVA, diferite setări iniţiale.
La parteneri - persoane fizice sau juridice - sunt folosite câmpuri specifice. 
Pentru a vă ajuta la instalare, sunt salvate screen-shot-uri cu setări în directorul 'inst_guide_images'.

**Important**, pentru a avea funcţionalitatea contabilă completă, mai sunt necesare alte câteva module.

    """,
    "demo" : [],
    "data" : ['security/ir.model.access.csv',
              'data/setup_data.xml',
              'data/res.country.state.csv',
              'data/res.bank.csv',
              'data/account_tax_code_template.xml',
              'data/account_chart.xml',
              'data/account_chart_template.xml',
              'data/account_tax_template.xml',              
              'data/fiscal_position_template.xml',
              'l10n_chart_ro_wizard.xml',
              'res_config_view.xml',
              'res_partner_view.xml',
              'data/setup.yml',
	],
    "test" : [], 
    "css": ['static/src/css/*.css'],   
    "auto_install": False,
    "installable": True,
    "images": ['inst_guide_images/Configure_Accounting_Data.png','inst_guide_images/Set_Your_Accounting_Options.png'],
}
