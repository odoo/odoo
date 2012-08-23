# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
    'name': 'Locadis Point Of Sale',
    'version': '1.0.1',
    'category': 'Point Of Sale',
    "sequence": 6,
    "summary": "Point of sale extensions for Locadis",
    'description': """
FIXME: product description
    """,
    'author': 'OpenERP SA',
    'images': [],
    'depends': ['point_of_sale'],
    'data':[
        'locadis_views.xml',
    ],
    'installable': True,
    'application': True,
    # Web client
    'js': [
        'static/src/js/main.js'
    ],
    'css': [
        'static/src/css/pos.css'
    ],
    'qweb': [
        'static/src/xml/pos.xml'
    ],
    'auto_install': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
