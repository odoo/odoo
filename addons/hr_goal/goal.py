# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2013 Tiny SPRL (<http://openerp.com>).
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

from datetime import date

class hr_goal_criteria(osv.Model):
	"""Goal criteria definition

	A criteria defining a way to set an objective and evaluate it
	Each module wanting to be able to set goals to the users needs to create
	a new goal_criteria
	"""
	_name = 'hr.goal.criteria'
	_description = 'Goal criteria'

	def get_evaluated_field_value(self, cr, user, ids, vals, context=None):
		"""Return the type of the 'evaluated_field' field"""
		for item in self.browse(cr, user, ids, context=context):
			return item.evaluated_field.ttype

	_columns = {
        'name': fields.char('Name'),
        'description': fields.char('Description'),
    	'evaluated_field': fields.many2one('ir.model.fields', 
    		string='Evaluated field'),
    }

class hr_goal(osv.Model):
	"""Goal instance for a user

	An individual goal for a user on a specified time period
	"""

	_name = 'hr.goal.instance'
	_description = 'Goal instance'

	_columns = {
		'criteria_id' : fields.many2one('hr.goal.criteria', string='Criteria'),
		'user_id' : fields.many2one('res.users', string='User'),
		'start_date' : fields.date('Start date'),
		'end_date' : fields.date('End date'),
		'to_reach' : fields.char('To reach'),
		'current' : fields.char('Current'),
	}

	def _compute_default_end_date(self, cr, uid, ids, field_name, arg, 
		context=None):
		hr_goal = self.browse(cr, uid, ids, context)
		if hr_goal.start_date:
			return hr_goal.start_date + datetime.timedelta(days=1)
		else:
			return fields.date.today() + datetime.timedelta(days=1)

	_defaults = {
        'start_date': fields.date.today,
        'end_date': _compute_default_end_date,
        'current': "",
    }



class hr_goal_definition(osv.Model):
	"""Goal definition

	Predifined goal for 'hr_goal_preset'
	"""

	_name = 'hr.goal.definition'
	_description = 'Goal definition'

	_columns = {
		'criteria_id' : fields.many2one('hr.goal.criteria',
			string='Criteria'),
		'default_to_reach' : fields.char('Default value to reach'),
	}


class hr_goal_preset(osv.Model):
	"""Goal preset

	Set of predifined goals to be able to automate goal settings or
	quickly apply several goals manually

	If both 'group_id' and 'period' are defined, the set will be assigned to the
	group for each period (eg: every 1st of each month if 'monthly' is selected)
	"""

	_name = 'hr.goal.preset'
	_description = 'Goal preset'

	_columns = {
		'name' : fields.char('Set name'),
		'definition_id' : fields.many2many('hr.goal.definition',
			string='Definition'),
		'group_id' : fields.many2one('res.groups', string='Group'),
		'period' : fields.selection(
			(
				('n','No automatic assigment'),
				('d','Daily'),
				('m','Monthly'),
				('y', 'Yearly')
			),
                   string='Period',
                   description='Period of automatic goal assigment, ignored if no group is selected'),
		}

	_defaults = {
        'period': 'n',
    }