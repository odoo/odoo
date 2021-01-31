# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2008-2012 NaN Projectes de Programari Lliure, S.L.
#                         http://www.NaN-tic.com
# Copyright (C) 2013 Tadeus Prastowo <tadeus.prastowo@infi-nity.com>
#                         Vikasa Infinity Anugrah <http://www.infi-nity.com>
# Copyright (C) 2019-Today Serpent Consulting Services Pvt. Ltd.
#                         (<http://www.serpentcs.com>)
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
    "name": "Jasper Reports",
    "version": "12.0.0.1.1",
    "summary": '''This module integrates Jasper Reports with Odoo.''',
    "author": "NaN·tic, Serpent Consulting Services Pvt. Ltd.",
    "website": "http://www.nan-tic.com, http://www.serpentcs.com",
    'images': [
        'images/jasper_reports-hover.png',
        'images/jasper_reports.png'
    ],
    "depends": [
        "sale", "jasper_load"
    ],
    "category": "Generic Modules/Jasper Reports",
    "demo": [
        'demo/jasper_report_demo.xml',
    ],
    "data": [
        'security/ir.model.access.csv',
        'data/jasper_data.xml',
        'wizard/jasper_create_data_template.xml',
        'views/webclient_templates.xml',
        'views/jasper_report_menu.xml',
        'views/report_xml_view.xml',
        'views/res_company_view.xml',
    ],
    "installable": True,
    "application": True,
    "license": "AGPL-3",
}
