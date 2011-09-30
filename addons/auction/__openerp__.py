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
    'name': 'Auction Management',
    'version': '1.0',
    'category': 'Associations',
    'complexity': "normal",
    'description': """
This module manages the records of artists, auction articles, buyers and sellers.
=================================================================================

It completely manages an auction such as managing bids,
keeping track of the sold articles along with the paid
and unpaid objects including delivery of the articles.

The dashboard for auction includes:
    * Latest Objects (list)
    * Latest Deposits (list)
    * Objects Statistics (list)
    * Total Adjudications (graph)
    * Min/Adj/Max (graph)
    * Objects By Day (graph)
    """,
    'author': 'OpenERP SA',
    'depends': ['base', 'account', 'hr_attendance'],
    'init_xml': ['auction_sequence.xml', 'auction_data.xml'],
    'update_xml': [
        'security/auction_security.xml',
        'security/ir.model.access.csv',
        'wizard/auction_lots_make_invoice_buyer_view.xml',
        'wizard/auction_lots_make_invoice_view.xml',
        'wizard/auction_taken_view.xml',
        'wizard/auction_lots_auction_move_view.xml',
        'wizard/auction_pay_buy_view.xml',
        'wizard/auction_lots_sms_send_view.xml',
        'wizard/auction_catalog_flagey_view.xml',
        'wizard/auction_lots_buyer_map_view.xml',
        'auction_view.xml',
        'auction_report.xml',
        'report/report_auction_view.xml',
        'auction_wizard.xml',
        'board_auction_view.xml',

    ],
    'demo_xml': ['auction_demo.xml','board_auction_demo.xml'],
    'test': ['test/auction.yml',
             'test/auction_report.yml',
             ],

    'installable': True,
    'active': False,
    'certificate': '0039333102717',
    'images': ['images/auction1.jpeg','images/auction2.jpeg','images/auction3.jpeg'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
