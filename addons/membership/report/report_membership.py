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
import decimal_precision as dp


STATE = [
    ('none', 'Non Member'),
    ('canceled', 'Cancelled Member'),
    ('old', 'Old Member'),
    ('waiting', 'Waiting Member'),
    ('invoiced', 'Invoiced Member'),
    ('free', 'Free Member'),
    ('paid', 'Paid Member'),
]


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
        'date_from': fields.datetime('Start Date', readonly=True, help="Start membership date"),
        'date_to': fields.datetime('End Date', readonly=True, help="End membership date"),
        'num_canceled': fields.integer('# Canceled', readonly=True),
        'num_old': fields.integer('# Old', readonly=True),
        'num_waiting': fields.integer('# Waiting', readonly=True),
        'num_invoiced': fields.integer('# Invoiced', readonly=True),
        'num_free': fields.integer('# Free', readonly=True),
        'num_paid': fields.integer('# Paid', readonly=True),
        'tot_pending': fields.float('Pending Amount', digits_compute= dp.get_precision('Account'), readonly=True),
        'tot_earned': fields.float('Earned Amount', digits_compute= dp.get_precision('Account'), readonly=True),
        'state':fields.selection(STATE, 'Membership State'),
        'partner_id': fields.many2one('res.partner', 'Members', readonly=True),
        'membership_id': fields.many2one('product.product', 'Membership Product', readonly=True),
        'user_id': fields.many2one('res.users', 'Salesman', readonly=True),
        'company_id': fields.many2one('res.company', 'Company', readonly=True)
}

    def init(self, cr):
        '''Create the view'''
        tools.drop_view_if_exists(cr, 'report_membership')
        cr.execute("""
    CREATE OR REPLACE VIEW report_membership AS (
        SELECT
        MIN(id) AS id,
        COUNT(num_canceled) AS num_canceled,
        COUNT(num_old) AS num_old,
        COUNT(num_waiting) AS num_waiting,
        COUNT(num_invoiced) AS num_invoiced,
        COUNT(num_free) AS num_free,
        COUNT(num_paid) AS num_paid,
        SUM(tot_pending) AS tot_pending,
        SUM(tot_earned) AS tot_earned,
        year,
        month,
        date_from,
        date_to,
        partner_id,
        membership_id,
        company_id,
        user_id,
        state
        FROM
        (SELECT
            CASE WHEN ml.state = 'canceled' THEN ml.id END AS num_canceled,
            CASE WHEN ml.state = 'old'      THEN ml.id END AS num_old,
            CASE WHEN ml.state = 'waiting'  THEN ml.id END AS num_waiting,
            CASE WHEN ml.state = 'invoiced' THEN ml.id END AS num_invoiced,
            CASE WHEN ml.state = 'free'     THEN ml.id END AS num_free,
            CASE WHEN ml.state = 'paid'     THEN ml.id END AS num_paid,
            CASE WHEN ml.state IN ('waiting', 'invoiced') THEN SUM(il.price_subtotal) ELSE 0 END AS tot_pending,
            CASE WHEN ml.state IN ('old', 'paid') THEN SUM(il.price_subtotal) ELSE 0 END AS tot_earned,
            TO_CHAR(ml.date_from, 'YYYY') AS year,
            TO_CHAR(ml.date_from, 'MM') AS month,
            TO_CHAR(ml.date_from, 'YYYY-MM-DD') AS date_from,
            TO_CHAR(ml.date_to, 'YYYY-MM-DD') AS date_to,
            ml.partner AS partner_id,
            MIN(ml.id) AS id,
            ml.membership_id AS membership_id,
            p.user_id AS user_id,
            ml.company_id AS company_id,
            ml.state AS state
            FROM membership_membership_line ml
            LEFT JOIN account_invoice_line il ON (ml.account_invoice_line = il.id)
            LEFT JOIN account_invoice ai ON (il.invoice_id = ai.id)
            LEFT JOIN res_partner p ON (ml.partner = p.id)
            GROUP BY
                 TO_CHAR(ml.date_from, 'YYYY'),
                 TO_CHAR(ml.date_from, 'MM'),
                 TO_CHAR(ml.date_from, 'YYYY-MM-DD'),
                 TO_CHAR(ml.date_to, 'YYYY-MM-DD'),
                 ml.partner,
                 ml.id,
                 p.user_id,
                 ml.company_id,
                 ml.state,
                 ml.membership_id) AS foo
        GROUP BY year, month, date_from, date_to, partner_id, user_id, membership_id, company_id, state)
                """)

report_membership()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
