# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
from openerp import tools
import openerp.addons.decimal_precision as dp

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
    '''Membership Analysis'''

    _name = 'report.membership'
    _description = __doc__
    _auto = False
    _rec_name = 'start_date'
    _columns = {
        'start_date': fields.date('Start Date', readonly=True),
        'date_to': fields.date('End Date', readonly=True, help="End membership date"),
        'num_waiting': fields.integer('# Waiting', readonly=True),
        'num_invoiced': fields.integer('# Invoiced', readonly=True),
        'num_paid': fields.integer('# Paid', readonly=True),
        'tot_pending': fields.float('Pending Amount', digits=0, readonly=True),
        'tot_earned': fields.float('Earned Amount', digits=0, readonly=True),
        'partner_id': fields.many2one('res.partner', 'Member', readonly=True),
        'associate_member_id': fields.many2one('res.partner', 'Associate Member', readonly=True),
        'membership_id': fields.many2one('product.product', 'Membership Product', readonly=True),
        'membership_state': fields.selection(STATE, 'Current Membership State', readonly=True),
        'user_id': fields.many2one('res.users', 'Salesperson', readonly=True),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
        'quantity': fields.integer("Quantity", readonly=True),
        }

    def init(self, cr):
        '''Create the view'''
        tools.drop_view_if_exists(cr, 'report_membership')
        cr.execute("""
        CREATE OR REPLACE VIEW report_membership AS (
        SELECT
        MIN(id) AS id,
        partner_id,
        count(membership_id) as quantity,
        user_id,
        membership_state,
        associate_member_id,
        membership_amount,
        date_to,
        start_date,
        COUNT(num_waiting) AS num_waiting,
        COUNT(num_invoiced) AS num_invoiced,
        COUNT(num_paid) AS num_paid,
        SUM(tot_pending) AS tot_pending,
        SUM(tot_earned) AS tot_earned,
        membership_id,
        company_id
        FROM
        (SELECT
            MIN(p.id) AS id,
            p.id AS partner_id,
            p.user_id AS user_id,
            p.membership_state AS membership_state,
            p.associate_member AS associate_member_id,
            p.membership_amount AS membership_amount,
            p.membership_stop AS date_to,
            p.membership_start AS start_date,
            CASE WHEN ml.state = 'waiting'  THEN ml.id END AS num_waiting,
            CASE WHEN ml.state = 'invoiced' THEN ml.id END AS num_invoiced,
            CASE WHEN ml.state = 'paid'     THEN ml.id END AS num_paid,
            CASE WHEN ml.state IN ('waiting', 'invoiced') THEN SUM(il.price_subtotal) ELSE 0 END AS tot_pending,
            CASE WHEN ml.state = 'paid' OR p.membership_state = 'old' THEN SUM(il.price_subtotal) ELSE 0 END AS tot_earned,
            ml.membership_id AS membership_id,
            p.company_id AS company_id
            FROM res_partner p
            LEFT JOIN membership_membership_line ml ON (ml.partner = p.id)
            LEFT JOIN account_invoice_line il ON (ml.account_invoice_line = il.id)
            LEFT JOIN account_invoice ai ON (il.invoice_id = ai.id)
            WHERE p.membership_state != 'none' and p.active = 'true'
            GROUP BY
              p.id,
              p.user_id,
              p.membership_state,
              p.associate_member,
              p.membership_amount,
              p.membership_start,
              ml.membership_id,
              p.company_id,
              ml.state,
              ml.id
        ) AS foo
        GROUP BY
            start_date,
            date_to,
            partner_id,
            user_id,
            membership_id,
            company_id,
            membership_state,
            associate_member_id,
            membership_amount
        )""")
