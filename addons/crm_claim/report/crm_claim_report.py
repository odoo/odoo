# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields,osv
from openerp import tools

AVAILABLE_PRIORITIES = [
   ('0', 'Low'),
   ('1', 'Normal'),
   ('2', 'High')
]


class crm_claim_report(osv.osv):
    """ CRM Claim Report"""

    _name = "crm.claim.report"
    _auto = False
    _description = "CRM Claim Report"

    _columns = {
        'user_id':fields.many2one('res.users', 'User', readonly=True),
        'team_id':fields.many2one('crm.team', 'Team', oldname='section_id', readonly=True),
        'nbr': fields.integer('# of Claims', readonly=True),  # TDE FIXME master: rename into nbr_claims
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
        'create_date': fields.datetime('Create Date', readonly=True, select=True),
        'claim_date': fields.datetime('Claim Date', readonly=True),
        'delay_close': fields.float('Delay to close', digits=(16,2),readonly=True, group_operator="avg",help="Number of Days to close the case"),
        'stage_id': fields.many2one ('crm.claim.stage', 'Stage', readonly=True,domain="[('team_ids','=',team_id)]"),
        'categ_id': fields.many2one('crm.claim.category', 'Category',readonly=True),
        'partner_id': fields.many2one('res.partner', 'Partner', readonly=True),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
        'priority': fields.selection(AVAILABLE_PRIORITIES, 'Priority'),
        'type_action': fields.selection([('correction','Corrective Action'),('prevention','Preventive Action')], 'Action Type'),
        'date_closed': fields.datetime('Close Date', readonly=True, select=True),
        'date_deadline': fields.date('Deadline', readonly=True, select=True),
        'delay_expected': fields.float('Overpassed Deadline',digits=(16,2),readonly=True, group_operator="avg"),
        'email': fields.integer('# Emails', size=128, readonly=True),
        'subject': fields.char('Claim Subject', readonly=True)
    }

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
