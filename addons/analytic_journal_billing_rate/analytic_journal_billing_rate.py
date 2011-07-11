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

from osv import fields,osv

class analytic_journal_rate_grid(osv.osv):

    _name="analytic_journal_rate_grid"
    _description= "Relation table between journals and billing rates"
    _columns={
        'journal_id': fields.many2one('account.analytic.journal', 'Analytic Journal', required=True,),
        'account_id': fields.many2one("account.analytic.account", "Analytic Account", required=True,),
        'rate_id': fields.many2one("hr_timesheet_invoice.factor", "Invoicing Rate",),
        }

analytic_journal_rate_grid()

class account_analytic_account(osv.osv):

    _inherit = "account.analytic.account"
    _columns = {
        'journal_rate_ids': fields.one2many('analytic_journal_rate_grid', 'account_id', 'Invoicing Rate per Journal'),
    }

account_analytic_account()

class hr_analytic_timesheet(osv.osv):

    _inherit = "hr.analytic.timesheet"


    def on_change_account_id(self, cr, uid, ids, account_id, user_id=False, unit_amount=0, journal_id=0):
        res = {}
        if not (account_id):
            #avoid a useless call to super
            return res 

        if not (journal_id):
            return super(hr_analytic_timesheet, self).on_change_account_id(cr, uid, ids,account_id, user_id, unit_amount)

        #get the browse record related to journal_id and account_id
        temp = self.pool.get('analytic_journal_rate_grid').search(cr, uid, [('journal_id', '=', journal_id),('account_id', '=', account_id) ])

        if not temp:
            #if there isn't any record for this journal_id and account_id
            return super(hr_analytic_timesheet, self).on_change_account_id(cr, uid, ids,account_id,user_id, unit_amount)
        else:
            #get the old values from super and add the value from the new relation analytic_journal_rate_grid
            r = self.pool.get('analytic_journal_rate_grid').browse(cr, uid, temp)[0]
            res.setdefault('value',{})
            res['value']= super(hr_analytic_timesheet, self).on_change_account_id(cr, uid, ids, account_id, user_id, unit_amount)['value']
            if r.rate_id.id:
                res['value']['to_invoice'] = r.rate_id.id
    
        return res


    def on_change_journal_id(self, cr, uid, ids, journal_id, account_id):
        res = {}
        if not (journal_id and account_id):
            return res 

        #get the browse record related to journal_id and account_id
        temp = self.pool.get('analytic_journal_rate_grid').search(cr, uid, [('journal_id', '=', journal_id),('account_id', '=', account_id) ])
        if temp:
            #add the value from the new relation analytic_user_funct_grid
            r = self.pool.get('analytic_journal_rate_grid').browse(cr, uid, temp)[0]
            res.setdefault('value',{})
            if r.rate_id.id:
                res['value']['to_invoice'] = r.rate_id.id
                return res
        to_invoice = self.pool.get('account.analytic.account').read(cr, uid, [account_id], ['to_invoice'])[0]['to_invoice']
        if to_invoice:
            res.setdefault('value',{})
            res['value']['to_invoice'] = to_invoice[0]

        return res

hr_analytic_timesheet()


class account_invoice(osv.osv):
    _inherit = "account.invoice"

    def _get_analytic_lines(self, cr, uid, id):
        iml = super(account_invoice, self)._get_analytic_lines(cr, uid, id)
        for il in iml:
            if il['account_analytic_id'] and il.get('analytic_lines', False):

                #get the browse record related to journal_id and account_id
                journal_id = il['analytic_lines'][0][2]['journal_id']
                account_id = il['analytic_lines'][0][2]['account_id']
                if journal_id and account_id:
                    temp = self.pool.get('analytic_journal_rate_grid').search(cr, uid, [('journal_id', '=', journal_id),('account_id', '=', account_id) ])

                    if temp:
                        r = self.pool.get('analytic_journal_rate_grid').browse(cr, uid, temp)[0]
                        il['analytic_lines'][0][2]['to_invoice'] = r.rate_id.id
        return iml

account_invoice()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

