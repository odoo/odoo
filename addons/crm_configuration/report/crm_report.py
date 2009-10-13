# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from osv import fields,osv

import tools.sql

AVAILABLE_STATES = [
    ('draft','Draft'),
    ('open','Open'),
    ('cancel', 'Cancelled'),
    ('done', 'Closed'),
    ('pending','Pending')
]

class report_crm_case_section_categ2(osv.osv):
    _name = "report.crm.case.section.categ2"
    _description = "Cases by section and category2"
    _auto = False
    _columns = {
        'name': fields.date('Month', readonly=True),
        'user_id':fields.many2one('res.users', 'User', readonly=True),
        'section_id':fields.many2one('crm.case.section', 'Section', readonly=True),
        'category2_id':fields.many2one('crm.case.category2', 'Type', readonly=True),
        'stage_id':fields.many2one('crm.case.stage', 'Stage', readonly=True),
        'amount_revenue': fields.float('Est.Revenue', readonly=True),
        'nbr': fields.integer('# of Cases', readonly=True),
        'state': fields.selection(AVAILABLE_STATES, 'State', size=16, readonly=True),        
        'delay_close': fields.char('Delay Close', size=20, readonly=True),
                }
    _order = 'category2_id, section_id'
    
    def init(self, cr):
        tools.sql.drop_view_if_exists(cr, "report_crm_case_section_categ2")
        cr.execute("""
              create view report_crm_case_section_categ2 as (
                select
                    min(c.id) as id,
                    to_char(c.create_date,'YYYY-MM')||'-01' as name,
                    c.user_id,
                    c.state,
                    c.category2_id,
                    c.stage_id,
                    c.section_id,
                    count(*) as nbr,
                    sum(planned_revenue) as amount_revenue,
                    to_char(avg(date_closed-c.create_date), 'DD"d" HH24:MI:SS') as delay_close
                from
                    crm_case c
                where c.category2_id is not null
                group by to_char(c.create_date,'YYYY-MM'), c.user_id, c.state, c.stage_id, c.category2_id, c.section_id)""")

report_crm_case_section_categ2()

class report_crm_case_section_stage(osv.osv):
    _name = "report.crm.case.section.stage"
    _description = "Cases by section and stage"
    _auto = False
    _columns = {
        'name': fields.date('Month', readonly=True),
        'user_id':fields.many2one('res.users', 'User', readonly=True),
        'section_id':fields.many2one('crm.case.section', 'Section', readonly=True),
        'categ_id':fields.many2one('crm.case.categ', 'Category', readonly=True),
        'stage_id':fields.many2one('crm.case.stage', 'Stage', readonly=True),
        'amount_revenue': fields.float('Est.Revenue', readonly=True),
        'nbr': fields.integer('# of Cases', readonly=True),
        'state': fields.selection(AVAILABLE_STATES, 'State', size=16, readonly=True),        
        'delay_close': fields.char('Delay Close', size=20, readonly=True),
                }
    _order = 'stage_id, section_id'
    
    def init(self, cr):
        tools.sql.drop_view_if_exists(cr, "report_crm_case_section_stage")
        cr.execute("""
              create view report_crm_case_section_stage as (
                select
                    min(c.id) as id,
                    to_char(c.create_date,'YYYY-MM')||'-01' as name,
                    c.user_id,
                    c.state,
                    c.stage_id,
                    c.section_id,
                    count(*) as nbr,
                    sum(planned_revenue) as amount_revenue,
                    to_char(avg(date_closed-c.create_date), 'DD"d" HH24:MI:SS') as delay_close
                from
                    crm_case c
                where c.stage_id is not null
                group by to_char(c.create_date,'YYYY-MM'), c.user_id, c.state, c.stage_id, c.section_id)""")

report_crm_case_section_stage()

class report_crm_case_section_categ_stage(osv.osv):
    _name = "report.crm.case.section.categ.stage"
    _description = "Cases by section, Category and stage"
    _auto = False
    _columns = {
        'name': fields.date('Month', readonly=True),
        'user_id':fields.many2one('res.users', 'User', readonly=True),
        'categ_id':fields.many2one('crm.case.categ', 'Category', readonly=True),
        'section_id':fields.many2one('crm.case.section', 'Section', readonly=True),
        'stage_id':fields.many2one('crm.case.stage', 'Stage', readonly=True),
        'nbr': fields.integer('# of Cases', readonly=True),
        'state': fields.selection(AVAILABLE_STATES, 'State', size=16, readonly=True),        
        'delay_close': fields.char('Delay Close', size=20, readonly=True),
                }
    _order = 'stage_id, section_id, categ_id'
    
    def init(self, cr):
        tools.sql.drop_view_if_exists(cr, "report_crm_case_section_categ_stage")
        cr.execute("""
              create view report_crm_case_section_categ_stage as (
                select
                    min(c.id) as id,
                    to_char(c.create_date,'YYYY-MM')||'-01' as name,
                    c.user_id,
                    c.categ_id,
                    c.state,
                    c.stage_id,
                    c.section_id,
                    count(*) as nbr,
                    to_char(avg(date_closed-c.create_date), 'DD"d" HH24:MI:SS') as delay_close
                from
                    crm_case c
                where c.categ_id is not null AND c.stage_id is not null
                group by to_char(c.create_date,'YYYY-MM'), c.user_id, c.categ_id, c.state, c.stage_id, c.section_id)""")

report_crm_case_section_categ_stage()

class report_crm_case_section_categ_categ2(osv.osv):
    _name = "report.crm.case.section.categ.categ2"
    _description = "Cases by section, Category and Category2"
    _auto = False
    _columns = {
        'name': fields.date('Month', readonly=True),
        'user_id':fields.many2one('res.users', 'User', readonly=True),
        'categ_id':fields.many2one('crm.case.categ', 'Category', readonly=True),
        'category2_id':fields.many2one('crm.case.category2', 'Type', readonly=True),
        'section_id':fields.many2one('crm.case.section', 'Section', readonly=True),
        'stage_id':fields.many2one('crm.case.stage', 'Stage', readonly=True),
        'nbr': fields.integer('# of Cases', readonly=True),
        'state': fields.selection(AVAILABLE_STATES, 'State', size=16, readonly=True),        
        'delay_close': fields.char('Delay Close', size=20, readonly=True),
                }
    _order = 'section_id, categ_id, category2_id'
    
    def init(self, cr):
        tools.sql.drop_view_if_exists(cr, "report_crm_case_section_categ_categ2")
        cr.execute("""
              create view report_crm_case_section_categ_categ2 as (
                select
                    min(c.id) as id,
                    to_char(c.create_date, 'YYYY-MM')||'-01' as name,
                    c.user_id,
                    c.categ_id,
                    c.category2_id,
                    c.state,
                    c.stage_id,
                    c.section_id,
                    count(*) as nbr,
                    to_char(avg(date_closed-c.create_date), 'DD"d" HH24:MI:SS') as delay_close
                from
                    crm_case c
                where c.categ_id is not null AND c.category2_id is not null
                group by to_char(c.create_date,'YYYY-MM'), c.user_id, c.categ_id, c.category2_id, c.state, c.stage_id, c.section_id)""")

report_crm_case_section_categ_categ2()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

