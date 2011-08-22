
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

from osv import fields,osv
import tools
from crm import crm

AVAILABLE_STATES = [
    ('draft','Draft'),
    ('open','Open'),
    ('cancel', 'Cancelled'),
    ('done', 'Closed'),
    ('pending','Pending')
]
class project_issue_report(osv.osv):
    _name = "project.issue.report"
    _auto = False

    _columns = {
        'name': fields.char('Year', size=64, required=False, readonly=True),
        'user_id':fields.many2one('res.users', 'Responsible', readonly=True),
        'section_id':fields.many2one('crm.case.section', 'Sale Team', readonly=True),
        'state': fields.selection(AVAILABLE_STATES, 'State', size=16, readonly=True),
        'month':fields.selection([('01', 'January'), ('02', 'February'), \
                                  ('03', 'March'), ('04', 'April'),\
                                  ('05', 'May'), ('06', 'June'), \
                                  ('07', 'July'), ('08', 'August'),\
                                  ('09', 'September'), ('10', 'October'),\
                                  ('11', 'November'), ('12', 'December')], 'Month', readonly=True),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
        'day': fields.char('Day', size=128, readonly=True),
        'opening_date': fields.date('Date of Opening', readonly=True),
        'creation_date': fields.date('Creation Date', readonly=True),
        'date_closed': fields.date('Date of Closing', readonly=True),
        'categ_id': fields.many2one('crm.case.categ', 'Category', domain="[('section_id','=',section_id),('object_id.model', '=', 'project.issue')]"),
        'type_id': fields.many2one('project.task.type', 'Stage'),
        'nbr': fields.integer('# of Issues', readonly=True),
        'working_hours_open': fields.float('Avg. Working Hours to Open', readonly=True),
        'working_hours_close': fields.float('Avg. Working Hours to Close', readonly=True),
        'delay_open': fields.float('Avg. Delay to Open', digits=(16,2), readonly=True, group_operator="avg",
                                       help="Number of Days to close the project issue"),
        'delay_close': fields.float('Avg. Delay to Close', digits=(16,2), readonly=True, group_operator="avg",
                                       help="Number of Days to close the project issue"),
        'company_id' : fields.many2one('res.company', 'Company'),
        'priority': fields.selection(crm.AVAILABLE_PRIORITIES, 'Priority'),
        'project_id':fields.many2one('project.project', 'Project',readonly=True),
        'version_id': fields.many2one('project.issue.version', 'Version'),
        'assigned_to' : fields.many2one('res.users', 'Assigned to',readonly=True),
        'partner_id': fields.many2one('res.partner','Partner',domain="[('object_id.model', '=', 'project.issue')]"),
        'canal_id': fields.many2one('res.partner.canal', 'Channel',readonly=True),
        'task_id': fields.many2one('project.task', 'Task',domain="[('object_id.model', '=', 'project.issue')]" ),
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
                    c.state,
                    c.user_id,
                    c.working_hours_open,
                    c.working_hours_close,
                    c.section_id,
                    c.categ_id,
                    c.type_id,
                    to_char(c.date_closed, 'YYYY-mm-dd') as date_closed,
                    c.company_id as company_id,
                    c.priority as priority,
                    c.project_id as project_id,
                    c.version_id as version_id,
                    1 as nbr,
                    c.assigned_to,
                    c.partner_id,
                    c.canal_id,
                    c.task_id,
                    date_trunc('day',c.create_date) as create_date,
                    extract('epoch' from (c.date_open-c.create_date))/(3600*24) as  delay_open,
                    extract('epoch' from (c.date_closed-c.date_open))/(3600*24) as  delay_close,
                    (SELECT count(id) FROM mail_message WHERE model='project.issue' AND res_id=c.id) AS email

                FROM
                    project_issue c
                WHERE c.categ_id IN (select id from crm_case_categ where object_id in (select id from ir_model where model = 'project.issue'))
            )""")

project_issue_report()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
