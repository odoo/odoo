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

class followup(osv.osv):
    _name = 'account_followup.followup'
    _description = 'Account Follow Up'
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'description': fields.text('Description'),
        'followup_line': fields.one2many('account_followup.followup.line', 'followup_id', 'Follow-Up'),
        'company_id': fields.many2one('res.company', 'Company'),
    }
    _defaults = {
        'company_id': lambda s, cr, uid, c: s.pool.get('res.company')._company_default_get(cr, uid, 'account_followup.followup', context=c),
    }
    
    def check_company_uniq(self, cr, uid, ids, context=None):
        sr_id = self.search(cr,uid,[],context=context)
        lines = self.browse(cr, uid, sr_id, context=context)
        company = []
        for l in lines:
            if l.company_id.id in company:
                return False
            if l.company_id.id not in company:
                company.append(l.company_id.id)
        return True
    _constraints = [
        (check_company_uniq, 'Only One Folllowup by Company.',['company_id'] )
        ]

followup()

class followup_line(osv.osv):
    _name = 'account_followup.followup.line'
    _description = 'Follow-Up Criteria'
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of follow-up lines."),
        'delay': fields.integer('Days of delay'),
        'start': fields.selection([('days','Net Days'),('end_of_month','End of Month')], 'Type of Term', size=64, required=True),
        'followup_id': fields.many2one('account_followup.followup', 'Follow Ups', required=True, ondelete="cascade"),
        'description': fields.text('Printed Message', translate=True),
    }
    _defaults = {
        'start': 'days',
    }

followup_line()

class account_move_line(osv.osv):
    _inherit = 'account.move.line'
    _columns = {
        'followup_line_id': fields.many2one('account_followup.followup.line', 'Follow-up Level'),
        'followup_date': fields.date('Latest Follow-up', select=True),
                }

account_move_line()

class res_company(osv.osv):
    _inherit = "res.company"
    _columns = {
        'follow_up_msg': fields.text('Follow-up Message', translate=True),
    }

    _defaults = {
        'overdue_msg': '''
Date: %(date)s

Dear %(partner_name)s,

Please find in attachment a reminder of all your unpaid invoices, for a total amount due of:

%(followup_amount).2f %(company_currency)s

Thanks,
--
%(user_signature)s
%(company_name)s
        '''
    }

res_company()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: