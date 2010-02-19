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

AVAILABLE_STATES = [
    ('draft','Draft'),
    ('open','Open'),
    ('cancel', 'Cancelled'),
    ('done', 'Closed'),
    ('pending','Pending')
]

class report_crm_case_user(osv.osv):
    _name = "report.crm.case.user"
    _description = "Cases by user and section"
    _auto = False
    _columns = {
        'name': fields.char('Year',size=64,required=False, readonly=True),
        'user_id':fields.many2one('res.users', 'User', readonly=True),
        'section_id':fields.many2one('crm.case.section', 'Section', readonly=True),        
        'nbr': fields.integer('# of Cases', readonly=True),
        'state': fields.selection(AVAILABLE_STATES, 'Status', size=16, readonly=True),
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'), ('05','May'), ('06','June'),
                                  ('07','July'), ('08','August'), ('09','September'), ('10','October'), ('11','November'), ('12','December')],'Month',readonly=True),
    }
    _order = 'name desc, user_id'
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_crm_case_user')
        cr.execute("""
            create or replace view report_crm_case_user as (
                select
                    min(c.id) as id,
                    to_char(c.create_date, 'YYYY') as name,
                    to_char(c.create_date, 'MM') as month,
                    c.state,
                    c.user_id,
                    c.section_id,
                    count(*) as nbr
                from
                    crm_case c
                group by to_char(c.create_date, 'YYYY'), to_char(c.create_date, 'MM'), c.state, c.user_id,c.section_id
            )""")
report_crm_case_user()

class report_crm_case_categ(osv.osv):
    _name = "report.crm.case.categ"
    _description = "Cases by section and category"
    _auto = False
    _columns = {
        'name': fields.char('Year',size=64,required=False, readonly=True),
        'section_id':fields.many2one('crm.case.section', 'Section', readonly=True),
        'nbr': fields.integer('# of Cases', readonly=True),
        'state': fields.selection(AVAILABLE_STATES, 'Status', size=16, readonly=True),
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'), ('05','May'), ('06','June'),
                                  ('07','July'), ('08','August'), ('09','September'), ('10','October'), ('11','November'), ('12','December')],'Month',readonly=True),
    }
    _order = 'name desc'
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_crm_case_categ')
        cr.execute("""
            create or replace view report_crm_case_categ as (
                select
                    min(c.id) as id,
                    to_char(c.create_date, 'YYYY') as name,
                    to_char(c.create_date, 'MM') as month,
                    c.state,
                    c.section_id,
                    count(*) as nbr
                from
                    crm_case c
                group by to_char(c.create_date, 'YYYY'), to_char(c.create_date, 'MM'), c.state,c.section_id
            )""")
report_crm_case_categ()


class report_crm_case_section(osv.osv):
    _name = "report.crm.case.section"
    _description = "Cases by Section"
    _auto = False
    
    _columns = {
        'name': fields.char('Year',size=64,required=False, readonly=True),
#        'user_id':fields.many2one('res.users', 'User', readonly=True),
        'section_id':fields.many2one('crm.case.section', 'Section', readonly=True),
        'nbr_cases': fields.integer('# of Cases', readonly=True),
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'), ('05','May'), ('06','June'),
                                  ('07','July'), ('08','August'), ('09','September'), ('10','October'), ('11','November'), ('12','December')],'Month',readonly=True),
    }
    _order = 'name desc'
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_crm_case_section')
        cr.execute("""
            create or replace view report_crm_case_section as (
                select
                    min(c.id) as id,
                    to_char(c.create_date, 'YYYY') as name,
                    to_char(c.create_date, 'MM') as month,
                    count(*) as nbr_cases,
                    c.section_id as section_id
                from
                    crm_case c
                group by to_char(c.create_date, 'YYYY'),to_char(c.create_date, 'MM'), c.section_id
            )""")
report_crm_case_section()

class report_crm_case_service_dashboard(osv.osv):
    _name = "report.crm.case.service.dashboard"
    _description = "Report of Closed and Open CRM Cases within past 15 days"
    _auto = False
    _columns = {
        'date': fields.datetime('Date', readonly=True),
        'date_deadline': fields.datetime('Deadline', readonly=True),
        'name': fields.char('Description', size=64, readonly=True),
        'user_id': fields.many2one('res.users', 'Responsible', readonly=True),
        'state': fields.selection(AVAILABLE_STATES, 'Status', size=16, readonly=True),
        'create_date' : fields.datetime('Create Date', readonly=True)
    }
    _order = 'create_date'
    
    def init(self, cr):
        cr.execute("""create or replace view report_crm_case_service_dashboard as (
            select
                cse.id as id, cse.date as date, cse.date_deadline as date_deadline,
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

class report_crm_case_section_stage(osv.osv):
    _name = "report.crm.case.section.stage"
    _description = "Cases by section and stage"
    _auto = False
    _columns = {
        'name': fields.char('Year',size=64,required=False, readonly=True),
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'), ('05','May'), ('06','June'),
                                  ('07','July'), ('08','August'), ('09','September'), ('10','October'), ('11','November'), ('12','December')],'Month',readonly=True),
        'user_id':fields.many2one('res.users', 'User', readonly=True),
        'section_id':fields.many2one('crm.case.section', 'Section', readonly=True),
        'nbr': fields.integer('# of Cases', readonly=True),
        'state': fields.selection(AVAILABLE_STATES, 'State', size=16, readonly=True),
                }
    _order = 'section_id'

    def init(self, cr):
        tools.sql.drop_view_if_exists(cr, "report_crm_case_section_stage")
        cr.execute("""
              create view report_crm_case_section_stage as (
                select
                    min(c.id) as id,
                    to_char(c.create_date,'YYYY') as name,
                    to_char(c.create_date, 'MM') as month,
                    c.user_id,
                    c.state,
                    c.section_id,
                    count(*) as nbr
                from
                    crm_case c
                group by to_char(c.create_date, 'YYYY'), to_char(c.create_date, 'MM'), c.user_id, c.state, c.section_id)""")

report_crm_case_section_stage()

class report_crm_case_section_type(osv.osv):
    _name = "report.crm.case.section.type"
    _description = "Cases by Section and Type"
    _auto = False
    _columns = {
        'name': fields.char('Year',size=64,required=False, readonly=True),
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'), ('05','May'), ('06','June'),
                                  ('07','July'), ('08','August'), ('09','September'), ('10','October'), ('11','November'), ('12','December')],'Month',readonly=True),
        'user_id':fields.many2one('res.users', 'User', readonly=True),
        'section_id':fields.many2one('crm.case.section', 'Section', readonly=True),
        'nbr': fields.integer('# of Cases', readonly=True),
        'state': fields.selection(AVAILABLE_STATES, 'State', size=16, readonly=True),
    }
    _order = 'section_id'
    
    def init(self, cr):
        tools.sql.drop_view_if_exists(cr, "report_crm_case_section_type")
        cr.execute("""
              create view report_crm_case_section_type as (
                select
                    min(c.id) as id,
                    to_char(c.create_date,'YYYY') as name,
                    to_char(c.create_date, 'MM') as month,
                    c.user_id,
                    c.state,
                    c.section_id,
                    count(*) as nbr
                from
                    crm_case c
                group by to_char(c.create_date, 'YYYY'), to_char(c.create_date, 'MM'), c.user_id, c.section_id, c.state)""")

report_crm_case_section_type()

class report_crm_case_section_categ_stage(osv.osv):
    _name = "report.crm.case.section.categ.stage"
    _description = "Cases by Section, Category and Stage"
    _auto = False
    _columns = {
        'name': fields.char('Year',size=64,required=False, readonly=True),
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'), ('05','May'), ('06','June'),
                                  ('07','July'), ('08','August'), ('09','September'), ('10','October'), ('11','November'), ('12','December')],'Month',readonly=True),
        'user_id':fields.many2one('res.users', 'User', readonly=True),
        'section_id':fields.many2one('crm.case.section', 'Section', readonly=True),
        'nbr': fields.integer('# of Cases', readonly=True),
        'state': fields.selection(AVAILABLE_STATES, 'State', size=16, readonly=True),
                }
    _order = 'section_id'

    def init(self, cr):
        tools.sql.drop_view_if_exists(cr, "report_crm_case_section_categ_stage")
        cr.execute("""
              create view report_crm_case_section_categ_stage as (
                select
                    min(c.id) as id,
                    to_char(c.create_date,'YYYY') as name,
                    to_char(c.create_date, 'MM') as month,
                    c.user_id,
                    c.state,
                    c.section_id,
                    count(*) as nbr
                from
                    crm_case c
                group by to_char(c.create_date, 'YYYY'), to_char(c.create_date, 'MM'),c.user_id, c.state, c.section_id)""")

report_crm_case_section_categ_stage()

class report_crm_case_section_categ_type(osv.osv):
    _name = "report.crm.case.section.categ.type"
    _description = "Cases by Section, Category and Type"
    _auto = False
    _columns = {
        'name': fields.char('Year',size=64,required=False, readonly=True),
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'), ('05','May'), ('06','June'),
                                  ('07','July'), ('08','August'), ('09','September'), ('10','October'), ('11','November'), ('12','December')],'Month',readonly=True),
        'user_id':fields.many2one('res.users', 'User', readonly=True),
        'section_id':fields.many2one('crm.case.section', 'Section', readonly=True),
        'nbr': fields.integer('# of Cases', readonly=True),
        'state': fields.selection(AVAILABLE_STATES, 'State', size=16, readonly=True),
    }
    _order = 'section_id'

    def init(self, cr):
        tools.sql.drop_view_if_exists(cr, "report_crm_case_section_categ_type")
        cr.execute("""
              create view report_crm_case_section_categ_type as (
                select
                    min(c.id) as id,
                    to_char(c.create_date, 'YYYY') as name,
                    to_char(c.create_date, 'MM') as month,
                    c.user_id,
                    c.state,
                    c.section_id,
                    count(*) as nbr
                from
                    crm_case c
                group by to_char(c.create_date, 'YYYY'), to_char(c.create_date, 'MM'),c.user_id, c.state, c.section_id)""")

report_crm_case_section_categ_type()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

