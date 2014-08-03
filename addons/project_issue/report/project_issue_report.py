
# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import fields, osv
from openerp import tools
from openerp.addons.crm import crm

class project_issue_report(osv.osv):
    _name = "project.issue.report"
    _auto = False

    _columns = {
        'name': fields.char('Year', size=64, required=False, readonly=True),
        'section_id':fields.many2one('crm.case.section', 'Sale Team', readonly=True),
        'month':fields.selection(fields.date.MONTHS, 'Month', readonly=True),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
        'day': fields.char('Day', size=128, readonly=True),
        'opening_date': fields.date('Date of Opening', readonly=True),
        'creation_date': fields.date('Creation Date', readonly=True),
        'date_closed': fields.date('Date of Closing', readonly=True),
        'date_last_stage_update': fields.date('Last Stage Update', readonly=True),
        'stage_id': fields.many2one('project.task.type', 'Stage'),
        'nbr': fields.integer('# of Issues', readonly=True),
        'working_hours_open': fields.float('Avg. Working Hours to Open', readonly=True, group_operator="avg"),
        'working_hours_close': fields.float('Avg. Working Hours to Close', readonly=True, group_operator="avg"),
        'delay_open': fields.float('Avg. Delay to Open', digits=(16,2), readonly=True, group_operator="avg",
                                       help="Number of Days to open the project issue."),
        'delay_close': fields.float('Avg. Delay to Close', digits=(16,2), readonly=True, group_operator="avg",
                                       help="Number of Days to close the project issue"),
        'company_id' : fields.many2one('res.company', 'Company'),
        'priority': fields.selection([('0','Low'), ('1','Normal'), ('2','High')], 'Priority'),
        'project_id':fields.many2one('project.project', 'Project',readonly=True),
        'version_id': fields.many2one('project.issue.version', 'Version'),
        'user_id' : fields.many2one('res.users', 'Assigned to',readonly=True),
        'partner_id': fields.many2one('res.partner','Contact'),
        'channel': fields.char('Channel', readonly=True, help="Communication Channel."),
        'task_id': fields.many2one('project.task', 'Task'),
        'email': fields.integer('# Emails', size=128, readonly=True),
    }

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'project_issue_report')
        cr.execute("""
            CREATE OR REPLACE VIEW project_issue_report AS (
                SELECT
                    c.id as id,
                    to_char(c.create_date, 'YYYY') as name,
                    to_char(c.create_date, 'MM') as month,
                    to_char(c.create_date, 'YYYY-MM-DD') as day,
                    to_char(c.date_open, 'YYYY-MM-DD') as opening_date,
                    to_char(c.create_date, 'YYYY-MM-DD') as creation_date,
                    date_trunc('day',c.date_last_stage_update) as date_last_stage_update,
                    c.user_id,
                    c.working_hours_open,
                    c.working_hours_close,
                    c.section_id,
                    c.stage_id,
                    to_char(c.date_closed, 'YYYY-mm-dd') as date_closed,
                    c.company_id as company_id,
                    c.priority as priority,
                    c.project_id as project_id,
                    c.version_id as version_id,
                    1 as nbr,
                    c.partner_id,
                    c.channel,
                    c.task_id,
                    date_trunc('day',c.create_date) as create_date,
                    c.day_open as delay_open,
                    c.day_close as delay_close,
                    (SELECT count(id) FROM mail_message WHERE model='project.issue' AND res_id=c.id) AS email

                FROM
                    project_issue c
                WHERE c.active= 'true'
            )""")


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
