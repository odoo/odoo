# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
from openerp import tools
from openerp.addons.crm import crm_stage


class crm_lead_report_assign(osv.osv):
    """ CRM Lead Report """
    _name = "crm.lead.report.assign"
    _auto = False
    _description = "CRM Lead Report"
    _columns = {
        'partner_assigned_id':fields.many2one('res.partner', 'Partner', readonly=True),
        'grade_id':fields.many2one('res.partner.grade', 'Grade', readonly=True),
        'user_id':fields.many2one('res.users', 'User', readonly=True),
        'country_id':fields.many2one('res.country', 'Country', readonly=True),
        'team_id':fields.many2one('crm.team', 'Sales Team', oldname='section_id', readonly=True),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
        'date_assign': fields.date('Assign Date', readonly=True),
        'create_date': fields.datetime('Create Date', readonly=True),
        'delay_open': fields.float('Delay to Assign',digits=(16,2),readonly=True, group_operator="avg",help="Number of Days to open the case"),
        'delay_close': fields.float('Delay to Close',digits=(16,2),readonly=True, group_operator="avg",help="Number of Days to close the case"),
        'delay_expected': fields.float('Overpassed Deadline',digits=(16,2),readonly=True, group_operator="avg"),
        'probability': fields.float('Avg Probability',digits=(16,2),readonly=True, group_operator="avg"),
        'probability_max': fields.float('Max Probability',digits=(16,2),readonly=True, group_operator="max"),
        'planned_revenue': fields.float('Planned Revenue',digits=(16,2),readonly=True),
        'probable_revenue': fields.float('Probable Revenue', digits=(16,2),readonly=True),
        'stage_id': fields.many2one ('crm.stage', 'Stage', domain="[('team_ids', '=', team_id)]"),
        'partner_id': fields.many2one('res.partner', 'Customer' , readonly=True),
        'opening_date': fields.datetime('Opening Date', readonly=True),
        'date_closed': fields.datetime('Close Date', readonly=True),
        'nbr': fields.integer('# of Cases', readonly=True),  # TDE FIXME master: rename into nbr_cases
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
        'priority': fields.selection(crm_stage.AVAILABLE_PRIORITIES, 'Priority'),
        'type':fields.selection([
            ('lead','Lead'),
            ('opportunity','Opportunity')
        ],'Type', help="Type is used to separate Leads and Opportunities"),
    }
    def init(self, cr):

        """
            CRM Lead Report
            @param cr: the current row, from the database cursor
        """
        tools.drop_view_if_exists(cr, 'crm_lead_report_assign')
        cr.execute("""
            CREATE OR REPLACE VIEW crm_lead_report_assign AS (
                SELECT
                    c.id,
                    c.date_open as opening_date,
                    c.date_closed as date_closed,
                    c.date_assign,
                    c.user_id,
                    c.probability,
                    c.probability as probability_max,
                    c.stage_id,
                    c.type,
                    c.company_id,
                    c.priority,
                    c.team_id,
                    c.partner_id,
                    c.country_id,
                    c.planned_revenue,
                    c.partner_assigned_id,
                    p.grade_id,
                    p.date as partner_date,
                    c.planned_revenue*(c.probability/100) as probable_revenue,
                    1 as nbr,
                    c.create_date as create_date,
                    extract('epoch' from (c.write_date-c.create_date))/(3600*24) as  delay_close,
                    extract('epoch' from (c.date_deadline - c.date_closed))/(3600*24) as  delay_expected,
                    extract('epoch' from (c.date_open-c.create_date))/(3600*24) as  delay_open
                FROM
                    crm_lead c
                    left join res_partner p on (c.partner_assigned_id=p.id)
            )""")
