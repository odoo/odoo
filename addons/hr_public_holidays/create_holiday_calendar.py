# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo Module
#    Copyright (C) 2015 Inline Technology Services (http://www.inlinetechnology.com)
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
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

from datetime import date
from datetime import datetime
from openerp import tools
from openerp.osv import fields, osv, expression
from openerp.tools.translate import _

class hr_holidays(osv.Model):
    _inherit="hr.holidays"
    
    _columns = {
        'holiday':fields.boolean('Holiday',readonly=True),
    }


class hr_holidays_line(osv.Model):
    _inherit="hr.holidays.public.line"
    
    def create_holiday_in_calendar(self,cr,uid,context=None):
    	hr_holidays_line_ids = self.search(cr, uid, [])
    	calendar_event_pool = self.pool.get('calendar.event')
    	hr_holidays_pool = self.pool.get('hr.holidays')
    	hr_holidays_status_pool = self.pool.get('hr.holidays.status')
    	if hr_holidays_line_ids:
    		for line_id in hr_holidays_line_ids:
    			print "line_id====",line_id
    			hr_holidays_line_obj = self.browse(cr,uid,line_id)
    			print "hr_holidays_line_obj====",hr_holidays_line_obj
    			if hr_holidays_line_obj.created != True:
    				date = hr_holidays_line_obj.date
    				#date_time = datetime.combine(date, datetime.min.time())
    				#print "\n\n**********",date_time
    				calander_vals = {
    					'name':hr_holidays_line_obj.name,
    					'start_datetime':date,
    					'stop_datetime':date,
    					'holiday':True,
    				}
    				
    				hr_holidays_status_vals = {
    					'name':hr_holidays_line_obj.name,
    					'color_name':'lightblue',
    				}
    				hr_holidays_status_id = hr_holidays_status_pool.create(cr,uid,hr_holidays_status_vals)
    				'''
    				hr_holidays_vals = {
    					'name':hr_holidays_line_obj.name,
    					'date_from':date,
    					'date_to':date,
    					'holiday_status_id':hr_holidays_status_id or False,
    					'employee_id':1,
    					'department_id':1,
    					'state':'draft',
                        'holiday':True,
    				}
    				print "\n\n=========",hr_holidays_vals
    				'''
    				user_ids = self.pool.get('res.users').search(cr, uid, [('name','!=','Demo Portal User')])
    				print "*****************users",user_ids
    				for user_id in user_ids:
						hr_holidays_vals = {
							'name':hr_holidays_line_obj.name,
							'date_from':date,
							'date_to':date,
							'holiday_status_id':hr_holidays_status_id or False,
							#'employee_id':user_id,
							'department_id':1,
							'state':'draft',
		                    'holiday':True,
						}
						calendar_event_pool.create(cr,user_id,calander_vals)
						hr_holidays_pool.create(cr,user_id,hr_holidays_vals)
    				self.write(cr,uid,line_id,{'created':True})
    				print "\n\n====DONE"	
        return True
                            
