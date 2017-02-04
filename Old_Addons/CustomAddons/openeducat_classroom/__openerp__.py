# -*- coding: utf-8 -*-
###############################################################################
#
#    Tech-Receptives Solutions Pvt. Ltd.
#    Copyright (C) 2009-TODAY Tech-Receptives(<http://www.techreceptives.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

{
    'name': 'KHF_extension classroom',
    'version': '1.0.1',
    'category': 'Openerp Education',
    "sequence": 3,
    'summary': 'VU KHF pritaikytas Openeducat auditorijų valdymo modulis',
    'complexity': "easy",
    'description': """
         VU  KHF Auditorijų valdymas.
    """,
    'author': 'Tech Receptives, Evaldas Grišius',
    'website': 'http://www.openeducat.org',
    'depends': ['openeducat_core', 'openeducat_facility'],
    'data': [
        'views/classroom_view.xml',
        'classroom_menu.xml',
        'security/ir.model.access.csv'
    ],
    'demo': [
        'demo/op.classroom.csv',
        'demo/op.facility.line.csv'
    ],
    'images': [
        'static/description/openeducat_classroom_banner.jpg',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
