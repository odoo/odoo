##############################################################################
#
# Copyright (c) 2004-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id: project.py 1005 2005-07-25 08:41:42Z nicoe $
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

from osv import fields,osv

AVAILABLE_STATES = [
	('draft','Draft'),
	('open','Open'),
	('cancel', 'Canceled'),
	('done', 'Closed'),
	('pending','Pending')
]

class report_crm_case_user(osv.osv):
	_name = "report.crm.case.user"
	_description = "Cases by user and section"
	_auto = False
	_columns = {
		'name': fields.date('Month', readonly=True),
		'user_id':fields.many2one('res.users', 'User', readonly=True, relate=True),
		'section_id':fields.many2one('crm.case.section', 'Section', readonly=True, relate=True),
		'amount_revenue': fields.float('Est.Revenue', readonly=True),
		'amount_costs': fields.float('Est.Cost', readonly=True),
		'amount_revenue_prob': fields.float('Est. Rev*Prob.', readonly=True),
		'nbr': fields.integer('# of Cases', readonly=True),
		'probability': fields.float('Avg. Probability', readonly=True),
		'state': fields.selection(AVAILABLE_STATES, 'State', size=16, readonly=True),
		'delay_close': fields.integer('Delay to close', readonly=True),
	}
	_order = 'name desc, user_id, section_id'
	def init(self, cr):
		cr.execute("""
			create or replace view report_crm_case_user as (
				select
					min(c.id) as id,
					substring(c.create_date for 7)||'-01' as name,
					c.state,
					c.user_id,
					c.section_id,
					count(*) as nbr,
					sum(planned_revenue) as amount_revenue,
					sum(planned_cost) as amount_costs,
					sum(planned_revenue*probability)::decimal(16,2) as amount_revenue_prob,
					avg(probability)::decimal(16,2) as probability,
					to_char(avg(date_closed-c.create_date), 'DD"d" HH24:MI:SS') as delay_close
				from
					crm_case c
				group by substring(c.create_date for 7), c.state, c.user_id, c.section_id
			)""")
report_crm_case_user()

class report_crm_case_categ(osv.osv):
	_name = "report.crm.case.categ"
	_description = "Cases by section and category"
	_auto = False
	_columns = {
		'name': fields.date('Month', readonly=True),
		'categ_id':fields.many2one('crm.case.categ', 'Category', readonly=True, relate=True),
		'section_id':fields.many2one('crm.case.section', 'Section', readonly=True, relate=True),
		'amount_revenue': fields.float('Est.Revenue', readonly=True),
		'amount_costs': fields.float('Est.Cost', readonly=True),
		'amount_revenue_prob': fields.float('Est. Rev*Prob.', readonly=True),
		'nbr': fields.integer('# of Cases', readonly=True),
		'probability': fields.float('Avg. Probability', readonly=True),
		'state': fields.selection(AVAILABLE_STATES, 'State', size=16, readonly=True),
		'delay_close': fields.integer('Delay Close', readonly=True),
	}
	_order = 'name desc, categ_id, section_id'
	def init(self, cr):
		cr.execute("""
			create or replace view report_crm_case_categ as (
				select
					min(c.id) as id,
					substring(c.create_date for 7)||'-01' as name,
					c.state,
					c.categ_id,
					c.section_id,
					count(*) as nbr,
					sum(planned_revenue) as amount_revenue,
					sum(planned_cost) as amount_costs,
					sum(planned_revenue*probability)::decimal(16,2) as amount_revenue_prob,
					avg(probability)::decimal(16,2) as probability,
					to_char(avg(date_closed-c.create_date), 'DD"d" HH24:MI:SS') as delay_close
				from
					crm_case c
				group by substring(c.create_date for 7), c.state, c.categ_id, c.section_id
			)""")
report_crm_case_categ()
