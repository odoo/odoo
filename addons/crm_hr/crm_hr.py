# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

from osv import fields,osv,orm
from crm import crm

AVAILABLE_STATES = [
    ('draft','New'),
    ('open','In Progress'),
    ('cancel', 'Refused'),
    ('done', 'Hired'),
    ('pending','Pending')
]

class crm_applicant(osv.osv):
    _name = "crm.applicant"
    _description = "Applicant Cases"
    _order = "id desc"
    _inherit ='crm.case'
    _columns = {
        'date_closed': fields.datetime('Closed', readonly=True),
        'date': fields.datetime('Date'),
        'priority': fields.selection(crm.AVAILABLE_PRIORITIES, 'Appreciation'),
        'job_id': fields.many2one('hr.job', 'Applied Job'),
        'salary_proposed': fields.float('Proposed Salary'),
        'salary_expected': fields.float('Expected Salary'),
        'availability': fields.integer('Availability (Days)'),
        'partner_name': fields.char("Applicant's Name", size=64),
        'partner_phone': fields.char('Phone', size=32),
        'partner_mobile': fields.char('Mobile', size=32),
        'stage_id': fields.many2one ('crm.case.stage', 'Stage', domain="[('section_id','=',section_id),('object_id.model', '=', 'crm.applicant')]"),
        'type_id': fields.many2one('crm.case.resource.type', 'Degree', domain="[('section_id','=',section_id),('object_id.model', '=', 'crm.applicant')]"),
        'department_id':fields.many2one('hr.department','Department'),
        'state': fields.selection(AVAILABLE_STATES, 'State', size=16, readonly=True),
    }
crm_applicant()
