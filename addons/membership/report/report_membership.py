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


class report_membership(osv.osv):
    '''Membership by Years'''

    _name = 'report.membership'
    _description = __doc__
    _auto = False
    _rec_name = 'year'
    _columns = {
        'year': fields.char('Year', size=4, readonly=True, select=1),
        'month':fields.selection([('01', 'January'), ('02', 'February'), \
                                  ('03', 'March'), ('04', 'April'),\
                                  ('05', 'May'), ('06', 'June'), \
                                  ('07', 'July'), ('08', 'August'),\
                                  ('09', 'September'), ('10', 'October'),\
                                  ('11', 'November'), ('12', 'December')], 'Month', readonly=True),
        'create_date': fields.datetime('Create Date', readonly=True),                          
        'canceled_number': fields.integer('Canceled', readonly=True),
        'waiting_number': fields.integer('Waiting', readonly=True),
        'invoiced_number': fields.integer('Invoiced', readonly=True),
        'paid_number': fields.integer('Paid', readonly=True),
        'canceled_amount': fields.float('Canceled', digits=(16, 2), readonly=True),
        'waiting_amount': fields.float('Waiting', digits=(16, 2), readonly=True),
        'invoiced_amount': fields.float('Invoiced', digits=(16, 2), readonly=True),
        'paid_amount': fields.float('Paid', digits=(16, 2), readonly=True),
        'currency': fields.many2one('res.currency', 'Currency', readonly=True,
            select=2),
            
        'state':fields.selection([('draft', 'Non Member'),
                                  ('cancel', 'Cancelled Member'),
                                    ('done', 'Old Member'),
                                   ('open', 'Invoiced Member'),
                                    ('free', 'Free Member'), ('paid', 'Paid Member')], 'State'),
        'partner_id': fields.many2one('res.partner', 'Members', readonly=True, select=3),
        'membership_id': fields.many2one('product.product', 'Membership', readonly=True, select=3) 
                

}

    def init(self, cr):
        '''Create the view'''
        tools.drop_view_if_exists(cr, 'report_membership')
        cr.execute("""
    CREATE OR REPLACE VIEW report_membership AS (
        SELECT
        MIN(id) as id,
        COUNT(ncanceled) as canceled_number,
        COUNT(npaid) as paid_number,
        COUNT(ninvoiced) as invoiced_number,
        COUNT(nwaiting) as waiting_number,
        SUM(acanceled) as canceled_amount,
        SUM(apaid) as paid_amount,
        SUM(ainvoiced) as invoiced_amount,
        SUM(awaiting) as waiting_amount,
        year,
        month,
        create_date,
        partner_id,
        membership_id,
        state,
        currency
        
        FROM (SELECT
            CASE WHEN ai.state = 'cancel' THEN ml.id END AS ncanceled,
            CASE WHEN ai.state = 'paid' THEN ml.id END AS npaid,
            CASE WHEN ai.state = 'open' THEN ml.id END AS ninvoiced,
            CASE WHEN (ai.state = 'draft' OR ai.state = 'proforma')
                THEN ml.id END AS nwaiting,
            CASE WHEN ai.state = 'cancel'
                THEN SUM(ail.price_unit * ail.quantity * (1 - ail.discount / 100))
            ELSE 0 END AS acanceled,
            CASE WHEN ai.state = 'paid'
                THEN SUM(ail.price_unit * ail.quantity * (1 - ail.discount / 100))
            ELSE 0 END AS apaid,
            CASE WHEN ai.state = 'open'
                THEN SUM(ail.price_unit * ail.quantity * (1 - ail.discount / 100))
            ELSE 0 END AS ainvoiced,
            CASE WHEN (ai.state = 'draft' OR ai.state = 'proforma')
                THEN SUM(ail.price_unit * ail.quantity * (1 - ail.discount / 100))
            ELSE 0 END AS awaiting,
            TO_CHAR(ml.date_from, 'YYYY') AS year,
            TO_CHAR(ml.date_from, 'MM')as month,
            TO_CHAR(ml.date_from, 'YYYY-MM-DD') as create_date,
            ai.partner_id AS partner_id,
            ai.currency_id AS currency,
            ai.state as state,
            MIN(ml.id) AS id,
            ml.membership_id AS membership_id
            FROM membership_membership_line ml
            JOIN (account_invoice_line ail
                LEFT JOIN account_invoice ai
                ON (ail.invoice_id = ai.id))
            ON (ml.account_invoice_line = ail.id)
            JOIN res_partner p
            ON (ml.partner = p.id)
            GROUP BY TO_CHAR(ml.date_from, 'YYYY'),  TO_CHAR(ml.date_from, 'MM'), TO_CHAR(ml.date_from, 'YYYY-MM-DD'), ai.state, ai.partner_id,
            ai.currency_id, ml.id, ml.membership_id) AS foo
        GROUP BY year, month, create_date, currency, partner_id, membership_id, state)
                """)
        
report_membership()

#
