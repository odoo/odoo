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
from tools.translate import _
import tools

class account_move_journal(osv.osv_memory):
    _name = "account.move.journal"
    _description = "Move journal"

    _columns = {
       'journal_id': fields.many2one('account.journal', 'Journal', required=True),
       'period_id': fields.many2one('account.period', 'Period', required=True),
                }


    def _get_period(self, cr, uid, context={}):
        """Return  default account period value"""
        ids = self.pool.get('account.period').find(cr, uid, context=context)
        period_id = False
        if len(ids):
            period_id = ids[0]
        return period_id

    def action_open_window(self, cr, uid, ids, context={}):
        """
        This function Open action move line window on given period and  Journal/Payment Mode
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: account move journal’s ID or list of IDs
        @return: dictionary of Open action move line window on given period and  Journal/Payment Mode

        """
        jp = self.pool.get('account.journal.period')
        mod_obj = self.pool.get('ir.model.data')
        for data in  self.read(cr, uid, ids, ['journal_id', 'period_id'],context=context):
            cr.execute('select id,name from ir_ui_view where model=%s and type=%s', ('account.move.line', 'form'))
            view_res = cr.fetchone()
            journal_id = data['journal_id']
            period_id = data['period_id']

            ids = jp.search(cr, uid, [('journal_id', '=', journal_id), \
                                        ('period_id', '=', period_id)],context=context)

            if not len(ids):
                name = self.pool.get('account.journal').read(cr, uid, [journal_id])[0]['name']
                state = self.pool.get('account.period').read(cr, uid, [period_id])[0]['state']
                if state == 'done':
                    raise osv.except_osv(_('UserError'), _('This period is already closed !'))
                company = self.pool.get('account.period').read(cr, uid, [period_id])[0]['company_id'][0]
                jp.create(cr, uid, {'name': name, 'period_id': period_id, 'journal_id': journal_id, 'company_id': company},context=context)

            ids = jp.search(cr, uid, [('journal_id', '=', journal_id), ('period_id', '=', period_id)],context=context)
            jp = jp.browse(cr, uid, ids, context=context)[0]
            name = (jp.journal_id.code or '') + ':' + (jp.period_id.code or '')

            result = mod_obj._get_id(cr, uid, 'account', 'view_account_move_line_filter')
            res = mod_obj.read(cr, uid, result, ['res_id'],context=context)

            return {
                'domain': "[('journal_id','=',%d), ('period_id','=',%d)]" % (journal_id, period_id),
                'name': name,
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.move.line',
                'view_id': view_res,
                'context': "{'journal_id': %d, 'period_id': %d}" % (journal_id, period_id),
                'type': 'ir.actions.act_window',
                'search_view_id': res['res_id']
                }


    _defaults = {
        'period_id': _get_period
                }

account_move_journal()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
