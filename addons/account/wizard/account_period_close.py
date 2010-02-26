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
import wizard
import netsvc
import pooler
import time
from tools.translate import _
import tools
from osv import fields, osv


class account_period_close(osv.osv_memory):
    """close period"""
    _name = "account.period.close"
    _description = "period close"
    _columns = {
                  'sure':fields.boolean('Check this box', required=False),
              }

    def _data_save(self, cr, uid, ids, context):
        """
         cr is the current row, from the database cursor,
         uid is the current user’s ID for security checks,
         ID is the account period close’s ID or list of IDs if we want more than one
         This function close period
         """
        
        mode = 'done'
        for form in self.read(cr, uid, ids): 
            if form['sure']:
                for id in context['active_ids']:
                    cr.execute('update account_journal_period set state=%s where period_id=%s', (mode, id))
                    cr.execute('update account_period set state=%s where id=%s', (mode, id))
            return {}

account_period_close()


