# See LICENSE file for full copyright and licensing details.

from datetime import datetime
from odoo.tests import common


class TestHostel(common.TransactionCase):

    def setUp(self):
        super(TestHostel, self).setUp()
        self.bed_type_obj = self.env['bed.type']
        self.hostel_type_obj = self.env['hostel.type']
        self.hostel_room_obj = self.env['hostel.room']
        self.hostel_student_obj = self.env['hostel.student']
        self.rector = self.env.ref('base.res_partner_2')
        self.student = self.env.ref('school.demo_student_student_5')
#       Create bed type
        self.bed_type = self.bed_type_obj.\
            create({'name': 'Single Bed',
                    'description': 'single bed type',
                    })
#        Create Hostel Type
        self.hostel_type = self.hostel_type_obj.\
            create({'name': 'Test Hostel',
                    'type': 'boys',
                    'rector': self.rector.id
                    })
#        Create Hostel Room
        self.hostel_room = self.hostel_room_obj.\
            create({'name': self.hostel_type.id,
                    'room_no': '101',
                    'student_per_room': '3',
                    'rent_amount': 1000,
                    'telephone': True,
                    'ac': True,
                    'private_bathroom': True
                    })
        self.hostel_room._compute_check_availability()
#        Create Hostel Student
        current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.hostel_student = self.hostel_student_obj.\
            create({'student_id': self.student.id,
                    'hostel_info_id': self.hostel_type.id,
                    'room_id': self.hostel_room.id,
                    'admission_date': current_date,
                    'duration': 2,
                    'bed_type': self.bed_type.id
                    })
        self.hostel_student.check_duration()
        self.hostel_student._compute_remaining_fee_amt()
        self.hostel_student._compute_rent()
        self.hostel_student._get_hostel_user()
        self.hostel_student.reservation_state()
        self.hostel_student.onchnage_discharge_date()
        self.hostel_student.discharge_state()
        self.hostel_student.student_expire()
        self.hostel_student.print_fee_receipt()

    def test_hostel(self):
        self.assertEqual(self.student.state, 'done')
        self.assertIn(self.hostel_room.name, self.hostel_type)
