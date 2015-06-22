# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import fields, models, tools
from openerp.addons.crm.models import crm

AVAILABLE_STATES = [
    ('draft', 'Draft'),
    ('open', 'Todo'),
    ('cancel', 'Cancelled'),
    ('done', 'Held'),
    ('pending', 'Pending')
]


class CrmPhoneCallReport(models.Model):
    """ Phone calls by user and team """

    _name = "crm.phonecall.report"
    _description = "Phone calls by user and team"
    _auto = False

    user_id = fields.Many2one('res.users', string='User', readonly=True)
    team_id = fields.Many2one('crm.team', string='Sales Team', oldname='section_id', readonly=True)
    priority = fields.Selection([('0', 'Low'), ('1', 'Normal'), ('2', 'High')])
    nbr = fields.Integer(string='# of Cases', readonly=True)  # TDE FIXME master: rename into nbr_cases
    state = fields.Selection(AVAILABLE_STATES, string='Status', readonly=True)
    create_date = fields.Datetime(string='Create Date', readonly=True, index=True)
    delay_close = fields.Float(string='Delay to close', digits=(16, 2), readonly=True, group_operator="avg", help="Number of Days to close the case")
    duration = fields.Float(digits=(16, 2), readonly=True, group_operator="avg")
    delay_open = fields.Float(string='Delay to open', digits=(16, 2), readonly=True, group_operator="avg", help="Number of Days to open the case")
    categ_id = fields.Many2one('crm.phonecall.category', string='Category')
    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    opening_date = fields.Datetime(string='Opening Date', readonly=True, index=True)
    date_closed = fields.Datetime(string='Close Date', readonly=True, index=True)

    def init(self, cr):

        """ Phone Calls By User And Team
            @param cr: the current row, from the database cursor,
        """
        tools.drop_view_if_exists(cr, 'crm_phonecall_report')
        cr.execute("""
            create or replace view crm_phonecall_report as (
                select
                    id,
                    c.date_open as opening_date,
                    c.date_closed as date_closed,
                    c.state,
                    c.user_id,
                    c.team_id,
                    c.categ_id,
                    c.partner_id,
                    c.duration,
                    c.company_id,
                    c.priority,
                    1 as nbr,
                    c.create_date as create_date,
                    extract('epoch' from (c.date_closed-c.create_date))/(3600*24) as  delay_close,
                    extract('epoch' from (c.date_open-c.create_date))/(3600*24) as  delay_open
                from
                    crm_phonecall c
            )""")
