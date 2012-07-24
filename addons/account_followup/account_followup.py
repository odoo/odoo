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

class followup(osv.osv):
    _name = 'account_followup.followup'
    _description = 'Account Follow-up'
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'description': fields.text('Description'),
        'followup_line': fields.one2many('account_followup.followup.line', 'followup_id', 'Follow-up'),
        'company_id': fields.many2one('res.company', 'Company', required=True),
    }
    _defaults = {
        'company_id': lambda s, cr, uid, c: s.pool.get('res.company')._company_default_get(cr, uid, 'account_followup.followup', context=c),
    }
    
followup()

class followup_line(osv.osv):
    _name = 'account_followup.followup.line'
    _description = 'Follow-up Criteria'
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
    def _check_description(self, cr, uid, ids, context=None):
        for line in self.browse(cr, uid, ids, context=context):
            if line.description:
                try:
                    line.description % {'partner_name': '', 'date':'', 'user_signature': '', 'company_name': ''}
                except:
                    return False
        return True

    _constraints = [
        (_check_description, 'Your description is invalid, use the right legend or %% if you want to use the percent character.', ['description']),
    ]

followup_line()

class account_move_line(osv.osv):
    _inherit = 'account.move.line'
    _columns = {
        'followup_line_id': fields.many2one('account_followup.followup.line', 'Follow-up Level'),
        'followup_date': fields.date('Latest Follow-up', select=True),
    }

account_move_line()

class account_move_partner_info(osv.osv):
    _inherit = 'account.move.partner.info'
    _columns = {
                'followup_date': fields.date('Latest Follow-up'),
                'max_followup_id':fields.many2one('account_followup.followup.line',
                                    'Max Follow Up Level' )
    }
    
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'account_move_partner_info')
        cr.execute("""
          create or replace view account_move_partner_info as (
                SELECT  p.id, p.id as partner_id, 
                max(p.last_reconciliation_date) as last_reconciliation_date,
                max(l.date) as latest_date, 
                count(l.id)  as move_lines_count,
                max(p.partner_move_count) as partner_move_count,
                max(l.followup_date) as followup_date,
                max(l.followup_line_id) as max_followup_id
                FROM account_move_line as l INNER JOIN res_partner AS p ON (l.partner_id = p.id)
                group by p.id
                )
        """)
account_move_partner_info()

class res_company(osv.osv):
    _inherit = "res.company"
    _columns = {
        'follow_up_msg': fields.text('Follow-up Message', translate=True),
    }

    _defaults = {
        'follow_up_msg': '''
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
