from odoo import api, fields, models
from odoo import tools


class AccountFollowupStat(models.Model):
    _name = "followup.stat"
    _description = "Follow-up Statistics"
    _rec_name = 'partner_id'
    _order = 'date_move'
    _auto = False

    partner_id = fields.Many2one('res.partner', 'Partner', readonly=True)
    date_move = fields.Date('First move', readonly=True)
    date_move_last = fields.Date('Last move', readonly=True)
    date_followup = fields.Date('Latest followup', readonly=True)
    followup_id = fields.Many2one('followup.line', 'Follow Ups', readonly=True, ondelete="cascade")
    balance = fields.Float('Balance', readonly=True)
    debit = fields.Float('Debit', readonly=True)
    credit = fields.Float('Credit', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True)

    @api.model
    def init(self):
        tools.drop_view_if_exists(self._cr, 'followup_stat')
        self._cr.execute("""
            create or replace view followup_stat as (
                SELECT
                    l.id as id,
                    l.partner_id AS partner_id,
                    min(l.date) AS date_move,
                    max(l.date) AS date_move_last,
                    max(l.followup_date) AS date_followup,
                    max(l.followup_line_id) AS followup_id,
                    sum(l.debit) AS debit,
                    sum(l.credit) AS credit,
                    sum(l.debit - l.credit) AS balance,
                    l.company_id AS company_id
                FROM
                    account_move_line l
                    LEFT JOIN account_account a ON (l.account_id = a.id)
                WHERE
                    a.account_type =  'asset_receivable' AND
                    l.full_reconcile_id is NULL AND
                    l.partner_id IS NOT NULL
                GROUP BY
                    l.id, l.partner_id, l.company_id
            )""")
