# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import tools
from openerp.addons.crm import crm
from openerp.osv import fields, osv

AVAILABLE_STATES = [
    ('draft', 'Draft'),
    ('open', 'Todo'),
    ('cancel', 'Cancelled'),
    ('done', 'Held'),
    ('pending', 'Pending')
]


class crm_phonecall_report(osv.osv):
    """ Phone calls by user and team """

    _name = "crm.phonecall.report"
    _description = "Phone calls by user and team"
    _auto = False

    _columns = {
        'user_id':fields.many2one('res.users', 'User', readonly=True),
        'team_id':fields.many2one('crm.team', 'Sales Team', oldname='section_id', readonly=True),
        'priority': fields.selection([('0','Low'), ('1','Normal'), ('2','High')], 'Priority'),
        'nbr': fields.integer('# of Cases', readonly=True),  # TDE FIXME master: rename into nbr_cases
        'state': fields.selection(AVAILABLE_STATES, 'Status', readonly=True),
        'create_date': fields.datetime('Create Date', readonly=True, select=True),
        'delay_close': fields.float('Delay to close', digits=(16,2),readonly=True, group_operator="avg",help="Number of Days to close the case"),
        'duration': fields.float('Duration', digits=(16,2),readonly=True, group_operator="avg"),
        'delay_open': fields.float('Delay to open',digits=(16,2),readonly=True, group_operator="avg",help="Number of Days to open the case"),
        'categ_id': fields.many2one('crm.phonecall.category', 'Category'),
        'partner_id': fields.many2one('res.partner', 'Partner' , readonly=True),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
        'opening_date': fields.datetime('Opening Date', readonly=True, select=True),
        'date_closed': fields.datetime('Close Date', readonly=True, select=True),
    }

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
