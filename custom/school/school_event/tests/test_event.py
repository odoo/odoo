from odoo.tests import common
from datetime import datetime
from dateutil.relativedelta import relativedelta as rd


class TestEvent(common.TransactionCase):

    def setUp(self):
        super(TestEvent, self).setUp()
        self.event_parameter_obj = self.env['school.event.parameter']
        self.school_event_obj = self.env['school.event']
        self.school_event_reg_obj = self.env['school.event.registration']
        self.school_id = self.env.ref('school.demo_school_1')
        self.hr_employee = self.env.ref('hr.employee_al')
        self.part_name = self.env.ref('school.demo_student_student_5')
        self.standard = self.env.ref('school.demo_standard_standard_2')
        currdt = datetime.now()
        new_dt = currdt - rd(days=7)
        start_dt = datetime.strftime(new_dt, '%m/%d/%Y')
        end_date = currdt + rd(days=8)
        end_dt = datetime.strftime(end_date, '%m/%d/%Y')
        event_start = currdt + rd(days=15)
        eve_start = datetime.strftime(event_start, '%m/%d/%Y')
        event_end = currdt + rd(days=20)
        eve_end = datetime.strftime(event_end, '%m/%d/%Y')
        # Event Parameter created
        self.event_parameter = self.event_parameter_obj.\
            create({'name': 'New Parameter'})
        # Create school event
        self.school_event = self.school_event_obj.\
            create({'name': 'New Event',
                    'code': self.school_id.id,
                    'start_reg_date': start_dt,
                    'last_reg_date': end_dt,
                    'start_date': eve_start,
                    'end_date': eve_end,
                    'contact_per_id': self.hr_employee.id,
                    'supervisor_id': self.hr_employee.id,
                    'part_standard_ids': [(6, 0, (self.standard.ids))],
                    'parameter_id': self.event_parameter.id,
                    'maximum_participants': 20,
                    })
        self.school_event._compute_participants()
        self.school_event._check_dates()
        self.school_event._check_all_dates()
        self.school_event._search(args=[], offset=0, limit=None,
                                  order=None, count=False,
                                  access_rights_uid=None)
        # Create event registration
        self.school_event_reg = self.school_event_reg_obj.\
            create({'part_name_id': self.part_name.id,
                    'name': self.school_event.id,
                    })
        self.school_event_reg.regi_cancel()
        self.school_event_reg.regi_confirm()
        self.school_event.event_open()
        self.school_event.event_close()
        self.school_event.event_draft()
        self.school_event.event_cancel()
        self.school_event.event_open()

    def test_event(self):
        self.assertEqual(self.school_event.contact_per_id.is_school_teacher,
                         True)
        self.assertEqual(self.school_event.supervisor_id.is_school_teacher,
                         True)
        self.assertEqual(self.school_event_reg.part_name_id.state, 'done')
