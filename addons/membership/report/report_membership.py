# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools

STATE = [
    ('none', 'Non Member'),
    ('canceled', 'Cancelled Member'),
    ('old', 'Old Member'),
    ('waiting', 'Waiting Member'),
    ('invoiced', 'Invoiced Member'),
    ('free', 'Free Member'),
    ('paid', 'Paid Member'),
]


class ReportMembership(models.Model):
    '''Membership Analysis'''

    _name = 'report.membership'
    _description = 'Membership Analysis'
    _auto = False
    _rec_name = 'start_date'

    start_date = fields.Date(string='Start Date', readonly=True)
    date_to = fields.Date(string='End Date', readonly=True)
    num_waiting = fields.Integer(string='# Waiting', readonly=True)
    num_invoiced = fields.Integer(string='# Invoiced', readonly=True)
    num_paid = fields.Integer(string='# Paid', readonly=True)
    tot_pending = fields.Float(string='Pending Amount', digits=0, readonly=True)
    tot_earned = fields.Float(string='Earned Amount', digits=0, readonly=True)
    partner_id = fields.Many2one('res.partner', string='Member', readonly=True)
    associate_member_id = fields.Many2one('res.partner', string='Associate Member', readonly=True)
    membership_id = fields.Many2one('product.product', string='Membership Product', readonly=True)
    membership_state = fields.Selection(STATE, string='Current Membership State', readonly=True)
    user_id = fields.Many2one('res.users', string='Salesperson', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    quantity = fields.Integer(readonly=True)

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
            %s
            %s
            %s
            %s
        )""" % (self._table, self._select(), self._from(), self._where(), self._group_by()))

    def _select(self):
        return """
        SELECT
            count(membership_id) as quantity,
            MIN(p.id) AS id,
            p.id AS partner_id,
            p.user_id AS user_id,
            p.membership_state AS membership_state,
            p.associate_member AS associate_member_id,
            p.membership_amount AS membership_amount,
            p.membership_stop AS date_to,
            p.membership_start AS start_date,
            COUNT(ml.id) FILTER (WHERE ml.state = 'waiting') AS num_waiting,
            COUNT(ml.id) FILTER (WHERE ml.state = 'invoiced') AS num_invoiced,
            COUNT(ml.id) FILTER (WHERE ml.state = 'paid') AS num_paid,
            SUM(aml.price_subtotal) FILTER (WHERE ml.state IN ('waiting', 'invoiced')) AS tot_pending,
            SUM(aml.price_subtotal) FILTER (WHERE ml.state = 'paid' OR p.membership_state = 'old') AS tot_earned,
            ml.membership_id AS membership_id,
            p.company_id AS company_id
        """

    def _from(self):
        return """
            FROM res_partner p
            LEFT JOIN membership_membership_line ml ON (ml.partner = p.id)
            LEFT JOIN account_move_line aml ON (ml.account_invoice_line = aml.id)
            LEFT JOIN account_move am ON (aml.move_id = am.id)
        """

    def _where(self):
        return """
            WHERE p.membership_state != 'none' and p.active = 'true'
        """

    def _group_by(self):
        return """
        GROUP BY
            start_date,
            date_to,
            p.id,
            p.user_id,
            ml.membership_id,
            p.company_id,
            p.membership_state,
            p.associate_member,
            p.membership_amount
        """
