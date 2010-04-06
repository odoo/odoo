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

from osv import fields, osv
import tools

AVAILABLE_STATES = [
    ('draft','Draft'),
    ('open','Open'),
    ('cancel', 'Cancelled'),
    ('done', 'Closed'),
    ('pending','Pending')
]

class crm_case_report(osv.osv):
    """ Cases and section """

    _name = "crm.case.report"
    _description = "Cases and section"
    _auto = False

    def _get_data(self, cr, uid, ids, field_name, arg, context={}):

        """ @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param ids: List of case and section Data’s IDs
            @param context: A standard dictionary for contextual values """

        res = {}
        state_perc = 0.0
        avg_ans = 0.0

        for case in self.browse(cr, uid, ids, context):
            if field_name != 'avg_answers':
                state = field_name[5:]
                cr.execute("select count(*) from crm_opportunity where \
                    section_id =%s and state='%s'"%(case.section_id.id, state))
                state_cases = cr.fetchone()[0]
                perc_state = (state_cases / float(case.nbr)) * 100

                res[case.id] = perc_state
            else:
                model_name = self._name.split('report.')
                if len(model_name) < 2:
                    res[case.id] = 0.0
                else:
                    model_name = model_name[1]

                    cr.execute("select count(*) from crm_case_log l, ir_model m \
                         where l.model_id=m.id and m.model = '%s'" , model_name)
                    logs = cr.fetchone()[0]

                    avg_ans = logs / case.nbr
                    res[case.id] = avg_ans

        return res

    _columns = {
        'name': fields.char('Year', size=64, required=False, readonly=True),
        'user_id':fields.many2one('res.users', 'User', readonly=True),
        'section_id':fields.many2one('crm.case.section', 'Section', readonly=True),
        'nbr': fields.integer('# of Cases', readonly=True),
        'state': fields.selection(AVAILABLE_STATES, 'State', size=16, readonly=True),
        'avg_answers': fields.function(_get_data, string='Avg. Answers', method=True, type="integer"),
        'perc_done': fields.function(_get_data, string='%Done', method=True, type="float"),
        'perc_cancel': fields.function(_get_data, string='%Cancel', method=True, type="float"),
        'month':fields.selection([('01', 'January'), ('02', 'February'), \
                                  ('03', 'March'), ('04', 'April'),\
                                  ('05', 'May'), ('06', 'June'), \
                                  ('07', 'July'), ('08', 'August'),\
                                  ('09', 'September'), ('10', 'October'),\
                                  ('11', 'November'), ('12', 'December')], 'Month', readonly=True),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
    }

    _order = 'name desc, user_id'

    def init(self, cr):

        """ @param cr: the current row, from the database cursor """

        tools.drop_view_if_exists(cr, 'crm_case_report')
        cr.execute("""
            create or replace view crm_case_report as (
                select
                    min(c.id) as id,
                    to_char(c.create_date, 'YYYY') as name,
                    to_char(c.create_date, 'MM') as month,
                    c.state,
                    c.user_id,
                    c.section_id,
                    c.company_id,
                    count(*) as nbr
                from
                    crm_case c
                group by to_char(c.create_date, 'YYYY'), to_char(c.create_date, 'MM'),\
                         c.state, c.user_id,c.section_id,c.company_id
            )""")

crm_case_report()


class report_crm_case_service_dashboard(osv.osv):
    """ Report of Closed and Open CRM Cases within past 15 days """

    _name = "report.crm.case.service.dashboard"
    _description = "Report of Closed and Open CRM Cases within past 15 days"
    _auto = False

    _columns = {
        'date_deadline': fields.datetime('Deadline', readonly=True),
        'name': fields.char('Description', size=64, readonly=True),
        'user_id': fields.many2one('res.users', 'Responsible', readonly=True),
        'state': fields.selection(AVAILABLE_STATES, 'Status', size=16, readonly=True),
        'create_date' : fields.datetime('Create Date', readonly=True)
    }

    _order = 'create_date'

    def init(self, cr):

        """ @param cr: the current row, from the database cursor """

        cr.execute("""create or replace view report_crm_case_service_dashboard as (
            select
                cse.id as id, cse.date_deadline as date_deadline,
                cse.name as name, cse.user_id as user_id,
                 cse.state as state,
                cse.create_date as create_date
            from
                crm_case cse
            where
                (cse.state='done')
                OR

                ((to_date(to_char(cse.create_date, 'YYYY-MM-dd'),'YYYY-MM-dd') <= CURRENT_DATE)
                    AND
                (to_date(to_char(cse.create_date, 'YYYY-MM-dd'),'YYYY-MM-dd') > (CURRENT_DATE-15))
                    AND
                    cse.state='open')
            )""")

report_crm_case_service_dashboard()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

