import re
import urllib2
import datetime
from schoolbell.calendar import icalendar

import wizard
import pooler

CALENDAR_URL = 'http://127.0.0.1:7180'

def _employee_get(self,cr,uid,context={}):
	ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=', uid)])
	if ids:
		return ids[0]
	return False

class RequestHandler(object):

	def __init__(self):
		self.auth_handler = urllib2.HTTPBasicAuthHandler()
		self.opener = urllib2.build_opener(self.auth_handler)

	def addAuthentication(self, username, password):
		self.auth_handler.add_password('zope', CALENDAR_URL, username, password)

def get_url(url, auth_data={}):
	req = RequestHandler()
	if auth_data:
		req.addAuthentication(auth_data['user'], auth_data['pass'])
	return req.opener.open(url).read()

def _start_date(uid, y, z):
	today = datetime.date.today()
	monday = today - datetime.timedelta(days=today.weekday())
	return monday.strftime('%Y-%m-%d')

def _end_date(uid, y, z):
	today = datetime.date.today()
	friday = today + datetime.timedelta(days=4-today.weekday())
	return friday.strftime('%Y-%m-%d')

ical_form = """<?xml version="1.0" ?>
<form string="Chose the dates">
	<field name="startdate" />
	<field name="enddate" />
	<field name="user_id" colspan="3"/>
</form>"""

ical_fields = {
	'startdate' : dict(string='Start date', type='date', required=True, default=_start_date),
	'enddate' : dict(string='End date', type='date', required=True, default=_end_date),
	'user_id' : dict(string=u'User', type='many2one', relation='res.users', required=True, default=lambda x,y,z:x),
	}

success_form = """<?xml version="1.0" ?>
<form string="Import successful">
	<separator string="Import successful" />
</form>"""

success_fields = {}

project_re = re.compile(r"^ *\[?(\d{1,4}\.?\d{0,3})\]? *(.*)", re.UNICODE)

class wizard_import_icalendar(wizard.interface):
	def import_ical(self, cr, uid, data, context):
		employee_id = _employee_get(pooler.get_pool(cr.dbname).get('hr.attendance'), cr, data['form']['user_id'])
		if not employee_id:
			raise wizard.except_wizard('No employee found for the user', 'Login ID: %s' % data['form']['user_id'])
		
		first, end = [datetime.date(*(map(int, x.split('-')))) for x in [data['form']['startdate'], data['form']['enddate']]]
		end = min(end, datetime.date.today())
		try:
			user_obj = pooler.get_pool(cr.dbname).get('res.users')
			user = user_obj.read(cr, uid, [data['form']['user_id']])
			events = icalendar.read_icalendar(get_url('%s/persons/%s/calendar.ics' % (CALENDAR_URL, user[0]['login']), {'user': 'manager', 'pass': 'schoolbell'}))
		except urllib2.HTTPError, e:
			raise wizard.except_wizard('Erreur HTTP', '%s - %s' % (e.code, e.msg))
		except IndexError:
			raise wizard.except_wizard('No user login found', 'Login ID: %s' % data['form']['user_id'])
		
		event_obj = pooler.get_pool(cr.dbname).get('res.partner.event')
		timesheet_line_obj = pooler.get_pool(cr.dbname).get('hr.analytic.timesheet')
		analytic_account_obj = pooler.get_pool(cr.dbname).get('account.analytic.account')
		for event in [e for e in events if first <= e.dtstart.date() <= end]:
			project_search = project_re.search(event.title)
			if not project_search:
				continue
			else:
				project_code, summary = project_search.groups()
			
			account_id = analytic_account_obj.name_search(cr, uid, project_code)
			if account_id:
				account_id = account_id[0][0]
				timesheet_line_id = timesheet_line_obj.search(cr, uid, [('event_ical_id', '=', event.unique_id)])
				if not timesheet_line_id:
					unit_id = timesheet_line_obj.default_get(cr, uid, ['product_uom_id','product_id'], {'user_id' : data['form']['user_id']})
					amount = timesheet_line_obj.on_change_unit_amount(cr, uid, [], unit_id['product_id'], event.duration.seconds / 3600.0, unit_id['product_uom_id'])
					if amount:
						amount = amount['value']['amount']
					timesheet_line_obj.create(cr, uid, {'name' : summary, 'date' : event.dtstart.strftime('%Y-%m-%d'), 'unit_amount' : event.duration.seconds / 3600.0,
														'user_id' :vdata['form']['user_id'], 'account_id' : account_id, 'amount' : amount,
														'event_ical_id' : event.unique_id},
											  {'user_id' : data['form']['user_id']})

				event_id = event_obj.search(cr, uid, [('event_ical_id', '=', event.unique_id)])
				if not event_id:
					account = pooler.get_pool(cr.dbname).get('account.analytic.account').read(cr, uid, [account_id], ['partner_id', 'contact_id'])
					if account:
						event_obj.create(cr, uid,
						  {'name' : summary,
						   'description' : event.description,
						   'partner_id' : account[0]['partner_id'][0],
						   'project_id' : account_id,
						   'user_id' : data['form']['user_id'],
						   'date' : event.dtstart.strftime('%Y-%m-%d %H:%M'),
						   'event_ical_id' : event.unique_id})
		return {}
	
	states = {
		'init' : {
			'actions' : [],
			'result' : {'type' : 'form', 'arch' : ical_form, 'fields' : ical_fields, 'state' : (('import', 'Import'), ('end', 'Cancel'))}
			},
		'import' : {
			'actions' : [import_ical],
			'result' : {'type' : 'form', 'arch' : success_form, 'fields' : success_fields, 'state' : (('end', 'Quit'),)}
			},
		}

wizard_import_icalendar('hr.ical_import')
