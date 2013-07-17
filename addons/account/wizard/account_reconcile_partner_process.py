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

import time

from openerp.osv import fields, osv

class account_partner_reconcile_process(osv.osv_memory):
    _name = 'account.partner.reconcile.process'
    _description = 'Reconcilation Process partner by partner'

    def _get_to_reconcile(self, cr, uid, context=None):
        cr.execute("""
                  SELECT p_id FROM (SELECT l.partner_id as p_id, SUM(l.debit) AS debit, SUM(l.credit) AS credit
                                    FROM account_move_line AS l LEFT JOIN account_account a ON (l.account_id = a.id)
                                                                LEFT JOIN res_partner p ON (p.id = l.partner_id)
                                    WHERE a.reconcile = 't'
                                    AND l.reconcile_id IS NULL
                                    AND  (%s >  to_char(p.last_reconciliation_date, 'YYYY-MM-DD') OR  p.last_reconciliation_date IS NULL )
                                    AND  l.state <> 'draft'
                                    GROUP BY l.partner_id) AS tmp
                              WHERE debit > 0
                              AND credit > 0
                """,(time.strftime('%Y-%m-%d'),)
        )
        return len(map(lambda x: x[0], cr.fetchall())) - 1

    def _get_today_reconciled(self, cr, uid, context=None):
        cr.execute(
                "SELECT l.partner_id " \
                "FROM account_move_line AS l LEFT JOIN res_partner p ON (p.id = l.partner_id) " \
                "WHERE l.reconcile_id IS NULL " \
                "AND %s =  to_char(p.last_reconciliation_date, 'YYYY-MM-DD') " \
                "AND l.state <> 'draft' " \
                "GROUP BY l.partner_id ",(time.strftime('%Y-%m-%d'),)
        )
        return len(map(lambda x: x[0], cr.fetchall())) + 1

    def _get_partner(self, cr, uid, context=None):
        move_line_obj = self.pool.get('account.move.line')

        partner = move_line_obj.list_partners_to_reconcile(cr, uid, context=context)
        if not partner:
            return False
        return partner[0][0]

    def data_get(self, cr, uid, to_reconcile, today_reconciled, context=None):
        return {'progress': (100 / (float(to_reconcile + today_reconciled) or 1.0)) * today_reconciled}

    def default_get(self, cr, uid, fields, context=None):
        res = super(account_partner_reconcile_process, self).default_get(cr, uid, fields, context=context)
        if 'to_reconcile' in res and 'today_reconciled' in res:
            data = self.data_get(cr, uid, res['to_reconcile'], res['today_reconciled'], context)
            res.update(data)
        return res

    def next_partner(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        move_line_obj = self.pool.get('account.move.line')
        res_partner_obj = self.pool.get('res.partner')

        partner_id = move_line_obj.read(cr, uid, context['active_id'], ['partner_id'])['partner_id']
        if partner_id:
            res_partner_obj.write(cr, uid, partner_id[0], {'last_reconciliation_date': time.strftime('%Y-%m-%d')}, context)
        #TODO: we have to find a way to update the context of the current tab (we could open a new tab with the context but it's not really handy)
        #TODO: remove that comments when the client side dev is done
        return {'type': 'ir.actions.act_window_close'}

    _columns = {
        'to_reconcile': fields.float('Remaining Partners', readonly=True, help='This is the remaining partners for who you should check if there is something to reconcile or not. This figure already count the current partner as reconciled.'),
        'today_reconciled': fields.float('Partners Reconciled Today', readonly=True, help='This figure depicts the total number of partners that have gone throught the reconciliation process today. The current partner is counted as already processed.'),
        'progress': fields.float('Progress', readonly=True, help='Shows you the progress made today on the reconciliation process. Given by \nPartners Reconciled Today \ (Remaining Partners + Partners Reconciled Today)'),
        'next_partner_id': fields.many2one('res.partner', 'Next Partner to Reconcile', readonly=True, help='This field shows you the next partner that will be automatically chosen by the system to go through the reconciliation process, based on the latest day it have been reconciled.'), # TODO: remove the readonly=True when teh client side will allow to update the context of existing tab, so that the user can change this value if he doesn't want to follow openerp proposal
    }

    _defaults = {
        'to_reconcile': _get_to_reconcile,
        'today_reconciled': _get_today_reconciled,
        'next_partner_id': _get_partner,
    }

account_partner_reconcile_process()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
