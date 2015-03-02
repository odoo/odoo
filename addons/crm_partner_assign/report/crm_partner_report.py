# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import fields, models, tools


class CrmPartnerReportAssign(models.Model):
    """ CRM Lead Report """
    _name = "crm.partner.report.assign"
    _auto = False
    _description = "CRM Partner Report"

    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    grade_id = fields.Many2one('res.partner.grade', string='Grade', readonly=True)
    activation = fields.Many2one('res.partner.activation', index=True)
    user_id = fields.Many2one('res.users', string='User', readonly=True)
    date_review = fields.Date(string='Latest Partner Review')
    date_partnership = fields.Date(string='Partnership Date')
    country_id = fields.Many2one('res.country', string='Country', readonly=True)
    team_id = fields.Many2one('crm.team', string='Sales Team', oldname='section_id', readonly=True)
    opp = fields.Integer(string='# of Opportunity',
                         readonly=True)  # TDE FIXME master: rename into nbr_opportunities
    turnover = fields.Float(readonly=True)
    period_id = fields.Many2one('account.period', string='Invoice Period', readonly=True)

    def init(self, cr):
        """
            CRM Lead Report
            @param cr: the current row, from the database cursor
        """
        tools.drop_view_if_exists(cr, 'CrmPartnerReportAssign')
        cr.execute(""" CREATE OR REPLACE VIEW CrmPartnerReportAssign AS (
                SELECT
                    coalesce(i.id, p.id - 1000000000) as id,
                    p.id as partner_id,
                    (SELECT country_id FROM res_partner a WHERE a.parent_id=p.id AND country_id is not null limit 1) as country_id,
                    p.grade_id,
                    p.activation,
                    p.date_review,
                    p.date_partnership,
                    p.user_id,
                    p.team_id,
                    (SELECT count(id) FROM crm_lead WHERE partner_assigned_id=p.id) AS opp,
                    i.price_total as turnover,
                    i.date
                FROM
                    res_partner p
                    left join account_invoice_report i
                        on (i.partner_id=p.id and i.type in ('out_invoice','out_refund') and i.state in ('open','paid'))
        )
        """)
