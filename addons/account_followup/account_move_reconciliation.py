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
import tools

class account_move_reconciliation(osv.osv):
    _inherit = 'account.move.reconciliation'
    _columns = {
                'followup_date': fields.date('Latest Follow-up'),
                'max_followup_id':fields.many2one('account_followup.followup.line',
                                    'Max Follow Up Level' )
    }
    
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'account_move_reconciliation')
        cr.execute("""
            CREATE or REPLACE VIEW account_move_reconciliation as (
                SELECT  move_line.partner_id as id, move_line.partner_id, 
                MAX(move_line.followup_date) as followup_date,
                MAX(move_line.followup_line_id) as max_followup_id,
                MAX(move_line.date) as latest_date
                FROM account_move_line as move_line where move_line.state <> 'draft'
                GROUP by move_line.partner_id
                )
        """)
account_move_reconciliation()