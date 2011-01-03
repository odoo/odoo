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
from osv import fields, osv

class auction_taken(osv.osv_memory):
    """
    Auction lots taken.
    """
    _name = "auction.taken"
    _description = "Auction taken"
    
    _columns = {
        'lot_ids':fields.many2many('auction.lots', 'auction_taken_rel', 'taken_id', 'lot_id', 'Lots Emportes'), 
    }
    
    def _to_xml(s):
        return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    def process(self, cr, uid, ids, context=None):
          """
          This Function update Auction lots state to taken_away.
          @param cr: the current row, from the database cursor.
          @param uid: the current user’s ID for security checks.
          @param ids: List of Auction taken’s IDs
          @return: dictionary of lot_ids fields with empty list 
          """
          if context is None:
              context={}
          lot_obj = self.pool.get('auction.lots')
          for current in self.browse(cr, uid, ids, context=context):
              for lot in current.lot_ids:
                  lot_obj.write(cr, uid, lot.id, {'state':'taken_away', 'ach_emp': True})
              return {'lot_ids': []}

auction_taken()
