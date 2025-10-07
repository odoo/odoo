# See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta as rd

from odoo import fields
from odoo.tests import common


class TestTransport(common.TransactionCase):
    def setUp(self):
        super(TestTransport, self).setUp()
        self.transport_driver_obj = self.env["res.partner"]
        self.student_transport_obj = self.env["student.transport"]
        self.transport_registration_obj = self.env["transport.registration"]
        self.transport_participant_obj = self.env["transport.participant"]
        self.school = self.env.ref("school.demo_school_1")
        self.student = self.env.ref("school.demo_student_student_5")
        self.transport_vehicle = self.env.ref("fleet.vehicle_1")
        currdt = fields.datetime.today()
        tr_start_dt = currdt
        tr_end_dt = currdt + rd(years=1)
        tr_end_date = tr_end_dt
        new_dt = currdt + rd(days=2)
        rg_start_date = new_dt
        rg_end_dt = new_dt + rd(months=+2)
        rg_end_date = rg_end_dt
        #        Create The Transport Root
        self.transport_root = self.student_transport_obj.create(
            {
                "name": "Transport-root-1",
                "start_date": tr_start_dt,
                "end_date": tr_end_date,
                "trans_vehicle_ids": [(4, self.transport_vehicle.id)],
            }
        )
        self.transport_root.transport_open()
        self.transport_root.transport_close()
        self.transport_root.participant_expire()

        #        Do One Registration of The Participant
        self.transport_registration = self.transport_registration_obj.create(
            {
                "student_id": self.student.id,
                "name": self.transport_root.id,
                "vehicle_id": self.transport_vehicle.id,
                "registration_month": 2,
            }
        )
        self.transport_registration.onchange_name()
        self.transport_registration.onchange_registration_month()
        self.transport_registration.trans_regi_confirm()
        self.transport_registration.trans_regi_cancel()
        #        Do one entry of the transport.participant
        self.transport_participant = self.transport_participant_obj.create(
            {
                "name": self.student.id,
                "transport_id": self.transport_root.id,
                "stu_pid_id": self.student.pid,
                "tr_reg_date": rg_start_date,
                "tr_end_date": rg_end_date,
                "months": 2,
                "vehicle_id": self.transport_vehicle.id,
                "amount": 2000,
            }
        )
        self.transport_participant._search([])
        self.transport_participant.set_over()

    def test_transport(self):
        self.assertEqual(self.student.state, "done")
