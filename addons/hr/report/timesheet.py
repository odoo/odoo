##############################################################################
#
# Copyright (c) 2004-2008 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id$
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

from mx import DateTime
from mx.DateTime import now

import netsvc
import pooler

from report.interface import report_rml
from report.interface import toxml

one_week = DateTime.RelativeDateTime(days=7)
num2day = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

def to_hour(h):
	return int(h), int(round((h - int(h)) * 60, 0))

class report_custom(report_rml):
	def create_xml(self, cr, uid, ids, datas, context):
		service = netsvc.LocalService('object_proxy')

		start_date = DateTime.strptime(datas['form']['init_date'], '%Y-%m-%d')
		end_date = DateTime.strptime(datas['form']['end_date'], '%Y-%m-%d')
		first_monday = start_date - DateTime.RelativeDateTime(days=start_date.day_of_week)
		last_monday = end_date + DateTime.RelativeDateTime(days=7 - end_date.day_of_week)

		if last_monday < first_monday:
			first_monday, last_monday = last_monday, first_monday

		user_xml = []
		
		jf_sql = """select hol.date_from, hol.date_to from hr_holidays as hol, hr_holidays_status as stat
					where hol.holiday_status = stat.id and stat.name = 'Public holidays' """
		cr.execute(jf_sql)
		jfs = []
		jfs = [(DateTime.strptime(l['date_from'], '%Y-%m-%d %H:%M:%S'), DateTime.strptime(l['date_to'], '%Y-%m-%d %H:%M:%S')) for l in cr.dictfetchall()]
		
		for employee_id in ids:
			emp = service.execute(cr.dbname, uid, 'hr.employee', 'read', [employee_id], ['id', 'name'])[0]
			monday, n_monday = first_monday, first_monday + one_week
			stop, week_xml = False, []
			user_repr = '''
			<user>
			  <name>%s</name>
			  %%s
			</user>
			''' % toxml(emp['name'])
			while monday != last_monday:
				#### Work hour calculation
				sql = '''
				select action, att.name
				from hr_employee as emp inner join hr_attendance as att
				     on emp.id = att.employee_id
				where att.name between '%s' and '%s' and emp.id = %s
				order by att.name
				'''
				for idx in range(7):
					cr.execute(sql, (monday, monday + DateTime.RelativeDateTime(days=idx+1), employee_id))
					attendences = cr.dictfetchall()
					week_wh = {}
					if attendences and attendences[0]['action'] == 'sign_out':
						attendences.insert(0, {'name': monday.strftime('%Y-%m-%d %H:%M:%S'), 'action':'sign_in'})
					if attendences and attendences[-1]['action'] == 'sign_in':
						attendences.append({'name' : n_monday.strftime('%Y-%m-%d %H:%M:%S'), 'action':'sign_out'})
					for att in attendences:
						dt = DateTime.strptime(att['name'], '%Y-%m-%d %H:%M:%S')
						if att['action'] == 'sign_out':
							week_wh[ldt.day_of_week] = week_wh.get(ldt.day_of_week, 0) + (dt - ldt).hours
						ldt = dt

				#### Theoretical workhour calculation
				week_twh = {}
				sql = '''
				select t.hour_from, t.hour_to
				from hr_timesheet as t
					 inner join (hr_timesheet_group as g inner join hr_timesheet_employee_rel as rel
						         on rel.tgroup_id = g.id and rel.emp_id = %s)
					 on t.tgroup_id = g.id
				where dayofweek = %s 
					  and date_from = (select max(date_from) 
									   from hr_timesheet inner join (hr_timesheet_employee_rel 
																		inner join hr_timesheet_group 
																		on hr_timesheet_group.id = hr_timesheet_employee_rel.tgroup_id
																			and hr_timesheet_employee_rel.emp_id = %s)
														 on hr_timesheet.tgroup_id = hr_timesheet_group.id
									   where dayofweek = %s and date_from <= '%s') 
				order by date_from desc
				'''
				for idx in range(7):
					day = monday + DateTime.RelativeDateTime(days=idx+1)
					# Is this a public holiday ?
					isPH = False
					for jf_start, jf_end in jfs:
						if jf_start <= day < jf_end:
							isPH = True
							break
					if isPH:
						week_twh[idx] = 0
					else:
						cr.execute(sql, (emp['id'], day.day_of_week, emp['id'], day.day_of_week, day))
						dhs = cr.dictfetchall()
						week_twh[idx] = reduce(lambda x,y:x+(DateTime.strptime(y['hour_to'], '%H:%M:%S') - DateTime.strptime(y['hour_from'], '%H:%M:%S')).hours,dhs, 0)

				#### Holiday calculation
				sql = '''
				select hol.date_from, hol.date_to, stat.name as status
				from hr_employee as emp 
					 inner join (hr_holidays as hol left join hr_holidays_status as stat
					             on hol.holiday_status = stat.id)
				     on emp.id = hol.employee_id
				where ((hol.date_from <= '%s' and hol.date_to >= '%s') 
				        or (hol.date_from < '%s' and hol.date_to >= '%s')
					    or (hol.date_from > '%s' and hol.date_to < '%s')
					   and stat.name != 'Public holidays') and emp.id = %s
				order by hol.date_from
				'''
				cr.execute(sql, (monday, monday, n_monday, n_monday, monday, n_monday, employee_id))
				holidays = cr.dictfetchall()
				week_hol = {}
				for hol in holidays:
					df = DateTime.strptime(hol['date_from'], '%Y-%m-%d %H:%M:%S')
					dt = DateTime.strptime(hol['date_to'], '%Y-%m-%d %H:%M:%S')
					for idx in range(7):
						day = monday + DateTime.RelativeDateTime(days=idx+1)
						if (df.year, df.month, df.day) <= (day.year, day.month, day.day) <= (dt.year, dt.month, dt.day):
							if (df.year, df.month, df.day) == (dt.year, dt.month, dt.day):
								week_hol[idx] = {'status' : hol['status'], 'hours' : (dt - df).hours}
							else:
								week_hol[idx] = {'status' : hol['status'], 'hours' : week_twh[idx]}
				
				# Week xml representation
				week_repr = ['<week>', '<weekstart>%s</weekstart>' % monday.strftime('%Y-%m-%d'), '<weekend>%s</weekend>' % n_monday.strftime('%Y-%m-%d')]
				for idx in range(7):
					week_repr.append('<%s>' % num2day[idx])
					week_repr.append('<theoretical>%sh%02d</theoretical>' % to_hour(week_twh[idx]))
					if idx in week_wh:
						week_repr.append('<workhours>%sh%02d</workhours>' % to_hour(week_wh[idx]))
					if idx in week_hol and week_hol[idx]['hours']:
						week_repr.append('<holidayhours type="%(status)s">%(hours)s</holidayhours>' % week_hol[idx])
					week_repr.append('</%s>' % num2day[idx])
				week_repr.append('<total>')
				week_repr.append('<theoretical>%sh%02d</theoretical>' % to_hour(reduce(lambda x,y:x+y, week_twh.values(), 0)))
				week_repr.append('<worked>%sh%02d</worked>' % to_hour(reduce(lambda x,y:x+y, week_wh.values(), 0)))
				week_repr.append('<holiday>%sh%02d</holiday>' % to_hour(reduce(lambda x,y:x+y, [day['hours'] for day in week_hol.values()], 0)))
				week_repr.append('</total>')
				week_repr.append('</week>')
				if len(week_repr) > 30: # 30 = minimal length of week_repr
					week_xml.append('\n'.join(week_repr))
				
				monday, n_monday = n_monday, n_monday + one_week
			user_xml.append(user_repr % '\n'.join(week_xml))
		
		xml = '''<?xml version="1.0" encoding="UTF-8" ?>
		<report>
		%s
		</report>
		''' % '\n'.join(user_xml)
		return self.post_process_xml_data(cr, uid, xml, context)

report_custom('report.hr.timesheet.allweeks', 'hr.employee', '', 'addons/hr/report/timesheet.xsl')
# vim:noexpandtab:tw=0
