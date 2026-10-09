# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo import tools


class FollowupStatByPartner(models.Model):
    _name = "followup.stat.by.partner"
    _description = "Follow-up Statistics by Partner"
    _rec_name = 'partner_id'
    _auto = False

    def _get_invoice_partner_id(self):
        for rec in self:
            rec.invoice_partner_id = rec.partner_id.address_get(
                adr_pref=['invoice']).get('invoice', rec.partner_id.id)

    partner_id = fields.Many2one('res.partner', 'Partner', readonly=True)
    date_move = fields.Date('First move', readonly=True)
    date_move_last = fields.Date('Last move', readonly=True)
    date_followup = fields.Date('Latest follow-up', readonly=True)
    max_followup_id = fields.Many2one('followup.line', 'Max Follow Up Level', readonly=True, ondelete="cascade")
    balance = fields.Float('Balance', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    invoice_partner_id = fields.Many2one('res.partner', compute='_get_invoice_partner_id', string='Invoice Address')

    @api.model
    def init(self):
        tools.drop_view_if_exists(self._cr, 'followup_stat_by_partner')
        self._cr.execute("""
            create view followup_stat_by_partner as (
                SELECT
                    l.partner_id * 10000::bigint + l.company_id as id,
                    l.partner_id AS partner_id,
                    min(l.date) AS date_move,
                    max(l.date) AS date_move_last,
                    max(l.followup_date) AS date_followup,
                    max(l.followup_line_id) AS max_followup_id,
                    sum(l.debit - l.credit) AS balance,
                    l.company_id as company_id
                FROM
                    account_move_line l
                    LEFT JOIN account_account a ON (l.account_id = a.id)
                WHERE
                    a.account_type = 'asset_receivable' AND
                    l.full_reconcile_id is NULL AND
                    l.partner_id IS NOT NULL
                    GROUP BY
                    l.partner_id, l.company_id
            )""")


