# -*- coding: utf-8 -*-

from openerp import models, fields
from openerp import tools


class CrmClaimReport(models.Model):

    """ CRM Claim Report"""

    _name = "crm.claim.report"
    _description = "CRM Claim Report"
    _auto = False

    user_id = fields.Many2one('res.users', string='User', readonly=True)
    team_id = fields.Many2one('crm.team', string='Team', oldname='section_id', readonly=True)
    nbr = fields.Integer(string='# of Claims', readonly=True)  # TDE FIXME master: rename into nbr_claims
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    create_date = fields.Datetime(string='Create Date', index=True, readonly=True)
    claim_date = fields.Datetime(string='Claim Date', readonly=True)
    delay_close = fields.Float(
        string='Delay to close', digits=(16, 2), group_operator="avg", readonly=True, help="Number of Days to close the case")
    stage_id = fields.Many2one('crm.stage', string='Stage', readonly=True, domain="[('team_ids', '=', team_id)]")
    categ_id = fields.Many2one('crm.claim.category', string='Category', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    priority = fields.Selection([('0', 'Low'), ('1', 'Normal'), ('2', 'High')], string='Priority')
    type_action = fields.Selection([('correction', 'Corrective Action'), ('prevention', 'Preventive Action')], string='Action Type')
    date_closed = fields.Datetime(string='Close Date', index=True, readonly=True)
    date_deadline = fields.Date(string='Deadline', index=True, readonly=True)
    delay_expected = fields.Float(string='Overpassed Deadline', digits=(16, 2), group_operator="avg", readonly=True)
    email = fields.Integer(string='# Emails', readonly=True)
    subject = fields.Char(string='Claim Subject', readonly=True)

    def init(self, cr):
        """ Display Number of cases And Team Name
        @param cr: the current row, from the database cursor,
         """

        tools.drop_view_if_exists(cr, 'crm_claim_report')
        cr.execute("""
            create or replace view crm_claim_report as (
                select
                    min(c.id) as id,
                    c.date as claim_date,
                    c.date_closed as date_closed,
                    c.date_deadline as date_deadline,
                    c.user_id,
                    c.stage_id,
                    c.team_id,
                    c.partner_id,
                    c.company_id,
                    c.categ_id,
                    c.name as subject,
                    count(*) as nbr,
                    c.priority as priority,
                    c.type_action as type_action,
                    c.create_date as create_date,
                    avg(extract('epoch' from (c.date_closed-c.create_date)))/(3600*24) as  delay_close,
                    (SELECT count(id) FROM mail_message WHERE model='crm.claim' AND res_id=c.id) AS email,
                    extract('epoch' from (c.date_deadline - c.date_closed))/(3600*24) as  delay_expected
                from
                    crm_claim c
                group by c.date,\
                        c.user_id,c.team_id, c.stage_id,\
                        c.categ_id,c.partner_id,c.company_id,c.create_date,
                        c.priority,c.type_action,c.date_deadline,c.date_closed,c.id
            )""")
