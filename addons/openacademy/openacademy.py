from openerp.osv import osv, fields

class Course (osv.Model):
	_name = "openacademy.course"
	_description = "OpenAcademy course"
	_column = {
		'name': fields.char('Course Title',size=128,required=True),
		'description': fields.text('Description'),
		'responsible_id': fields.many2one('res.users',string='responsible',ondelete='set null'),
		'session_ids': fields.one2many('openacademy.session','course_id','Session'),
	}
class Session(osv.Model):
	_name = 'openacademy.session'
	_description = "OpenAcademy session"
	_columns = {
		'name': fields.char('Session Title', size=128, required=True),
		'start_date': fields.date('Start Date'),
		'duration': fields.float('Duration', digits=(6,2), help="Duration in days"),
		'seats': fields.integer('Number of seats'),
		'instructor_id': fields.many2one('res.partner','Intructor'),
		'course_id': fields.many2one('openacademy.course','course',required=True,ondelete='cascade'),
		'attendee_ids': fields.one2many('openacademy.attendee','session_id','Attendees'),
	}
class Attendee(osv.Model):
	_name = 'openacademy.attendee'
	_description = "OpenAcademy Attendee"
	_columns = {
		'partner_id': fields.many2one('res.partner','Partner',required=True,ondelete='cascade'),
		'session_id': fields.many2one('openacademy.session','Session',required=True,ondelete='cascade'),
	}