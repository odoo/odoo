# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
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
    'name': 'Auction module',
    'version': '1.0',
    'category': 'Generic Modules/Auction',
    'description': """This module provides functionality to 
     manage artists, articles, sellers, buyers and auction.
     Manage bids, track of sold, paid and unpaid objects.
     Delivery Management. 
    """,
    'author': 'Tiny',
    'depends': ['base', 'account', 'hr_attendance'],
    'init_xml': ['auction_sequence.xml'],
    'update_xml': [
        'security/ir.model.access.csv',
        'auction_view.xml',
        'auction_report.xml',
        'auction_wizard.xml'
    ],
    'demo_xml': ['auction_demo.xml'],
    'installable': True,
    'active': False,
    'certificate': '0039333102717',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
