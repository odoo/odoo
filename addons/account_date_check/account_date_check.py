# -*- encoding: utf-8 -*-
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

from osv import fields
from osv import osv
import time
import netsvc

import ir
from mx import DateTime
import pooler
from tools import config
from tools.translate import _

class account_journal(osv.osv):
    _inherit='account.journal'
    _name='account.journal'
    _columns = {
        'allow_date':fields.boolean('Allows date not in the period'),
    }
    _defaults = {
        'allow_date': lambda *a: 1,
        }
account_journal()

class account_move_line(osv.osv):
    _inherit='account.move.line'
    _name='account.move.line'

    def check_date(self, cr, uid, vals, context=None, check=True):
        if not context:
            context = {}
        if 'date' in vals.keys():
            if 'journal_id' in vals and 'journal_id' not in context:
                journal_id = vals['journal_id']
            if 'period_id' in vals and 'period_id' not in context:
                period_id = vals['period_id']
            elif 'journal_id' not in context and 'move_id' in vals:
                m = self.pool.get('account.move').browse(cr, uid, vals['move_id'])
                journal_id = m.journal_id.id
                period_id = m.period_id.id
            else:
                journal_id = context['journal_id']
                period_id = context['period_id']
            journal = self.pool.get('account.journal').browse(cr,uid,[journal_id])[0]
            if not journal.allow_date:
                period=self.pool.get('account.period').browse(cr,uid,[period_id])[0]

                date = time.strptime(vals['date'][:10], '%Y-%m-%d')
                if not (date >= time.strptime(period.date_start,'%Y-%m-%d')
                        and date <= time.strptime(period.date_stop,'%Y-%m-%d') ):

                    raise osv.except_osv(_('Error'),_('The date of your account move is not in the defined period !'))
        else:
            return True

    def write(self, cr, uid, ids, vals, context=None, check=True, update_check=True):
        flag=self.check_date(cr, uid, vals, context, check)
        result = super(account_move_line, self).write(cr, uid, ids, vals, context, check, update_check)
        return result
    def create(self, cr, uid, vals, context=None, check=True):
        flag=self.check_date(cr, uid, vals, context, check)
        result = super(account_move_line, self).create(cr, uid, vals, context, check)
        return result
account_move_line()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

