# -*- coding: utf-8 -*-

from openerp import api, fields, models
from openerp import tools


class CrmHelpdeskReport(models.Model):
    """ Helpdesk report after Sales Services """

    _name = "crm.helpdesk.report"
    _description = "Helpdesk report after Sales Services"
    _auto = False

    date = fields.Datetime(string='Date', readonly=True)
    user_id = fields.Many2one('res.users', string='User', readonly=True)
    team_id = fields.Many2one('crm.team', string='Team', oldname='section_id', readonly=True)
    nbr_requests = fields.Integer(string='# of Requests', readonly=True)
    state = fields.Selection([('draft', 'Draft'),
                            ('open', 'Open'),
                            ('cancel', 'Cancelled'),
                            ('done', 'Closed'),
                            ('pending', 'Pending')], string='Status', readonly=True)
    delay_close = fields.Float(string='Delay to Close', digits=(16,2), readonly=True, group_operator="avg")
    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    date_deadline = fields.Date(string='Deadline', index=True)
    priority = fields.Selection([('5', 'Lowest'),
                                ('4', 'Low'),
                                ('3', 'Normal'),
                                ('2', 'High'),
                                ('1', 'Highest')], string='Priority')
    channel_id = fields.Many2one('utm.medium', string='Channel')
    categ_id = fields.Many2one('crm.helpdesk.category', string='Category')
    planned_cost = fields.Float(string='Planned Costs')
    create_date = fields.Datetime(string='Creation Date', readonly=True, index=True)
    date_closed = fields.Datetime(string='Close Date', readonly=True, index=True)
    delay_expected = fields.Float(string='Overpassed Deadline', digits=(16,2), readonly=True, group_operator="avg")
    email = fields.Integer(string='# Emails', size=128, readonly=True)

    def init(self, cr):

        """
            Display Deadline ,Responsible user, partner ,Department
            @param cr: the current row, from the database cursor
        """

        tools.drop_view_if_exists(cr, 'crm_helpdesk_report')
        cr.execute("""
            create or replace view crm_helpdesk_report as (
                select
                    min(c.id) as id,
                    c.date as date,
                    c.create_date,
                    c.date_closed,
                    c.state,
                    c.user_id,
                    c.team_id,
                    c.partner_id,
                    c.company_id,
                    c.priority,
                    c.date_deadline,
                    c.categ_id,
                    c.channel_id,
                    c.planned_cost,
                    count(*) as nbr_requests,
                    extract('epoch' from (c.date_closed-c.create_date))/(3600*24) as  delay_close,
                    (SELECT count(id) FROM mail_message WHERE model='crm.helpdesk' AND res_id=c.id AND type = 'email') AS email,
                    abs(avg(extract('epoch' from (c.date_deadline - c.date_closed)))/(3600*24)) as delay_expected
                from
                    crm_helpdesk c
                where c.active = 'true'
                group by c.date,\
                     c.state, c.user_id,c.team_id,c.priority,\
                     c.partner_id,c.company_id,c.date_deadline,c.create_date,c.date,c.date_closed,\
                     c.categ_id,c.channel_id,c.planned_cost,c.id
            )""")
