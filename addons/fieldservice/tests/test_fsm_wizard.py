# Copyright (C) 2019 - TODAY, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class FSMWizard(TransactionCase):
    """
    Test used to check that the base functionalities of Field Service.
    - test_convert_location: tests that a res.partner can be converted
    into a fsm.location.
    - test_convert_person: tests that a res.partner can be converted into
    a fsm.person.
    - test_convert_sublocation: tests that the sub-contacts on a
    res.partner are converted into Other Addresses.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Wizard = cls.env["fsm.wizard"]
        cls.test_partner = cls.env.ref("fieldservice.test_partner")
        cls.test_parent_partner = cls.env.ref("fieldservice.test_parent_partner")
        cls.test_loc_partner = cls.env.ref("fieldservice.test_loc_partner")
        cls.test_location = cls.env.ref("fieldservice.test_location")
        cls.test_person = cls.env.ref("fieldservice.test_person")

    def test_convert_location(self):
        ctx = {
            "active_model": "res.partner",
            "active_id": self.test_parent_partner.id,
            "active_ids": self.test_parent_partner.ids,
        }
        ctx1 = {
            "active_model": "res.partner",
            "active_id": self.test_loc_partner.id,
            "active_ids": self.test_loc_partner.ids,
        }

        wiz_1 = self.Wizard.with_context(**ctx).create(
            {
                "fsm_record_type": "person",
            }
        )
        wiz_2 = self.Wizard.with_context(**ctx).create(
            {
                "fsm_record_type": "location",
            }
        )
        wiz_3 = self.Wizard.with_context(**ctx1).create(
            {
                "fsm_record_type": "location",
            }
        )

        wiz_1.action_convert()
        wiz_2.action_convert()
        with self.assertRaises(UserError):
            wiz_3.action_convert()
        # convert test_partner to FSM Location
        self.Wizard.action_convert_location(self.test_partner)

        # check if there is a new FSM Location with name 'Test Partner'
        self.wiz_location = self.env["fsm.location"].search(
            [("name", "=", "Test Partner")]
        )

        # check if 'Test Partner' creation successful and fields copied over
        self.assertEqual(self.test_location.phone, self.wiz_location.phone)
        self.assertEqual(self.test_location.email, self.wiz_location.email)

    def test_convert_person(self):
        # convert test_partner to FSM Person
        ctx2 = {
            "active_model": "res.partner",
            "active_id": self.test_partner.id,
            "active_ids": self.test_partner.ids,
        }
        wiz = self.Wizard.with_context(**ctx2).create(
            {
                "fsm_record_type": "person",
            }
        )
        wiz.action_convert()
        with self.assertRaises(UserError):
            self.Wizard.action_convert_person(self.test_partner)

        # check if there is a new FSM Person with name 'Test Partner'
        self.wiz_person = self.env["fsm.person"].search([("name", "=", "Test Partner")])
        # check if 'Test Partner' creation successful and fields copied over
        self.assertEqual(self.test_person.phone, self.wiz_person.phone)
        self.assertEqual(self.test_person.email, self.wiz_person.email)

    def test_convert_sublocation(self):
        # convert Parent Partner to FSM Location
        self.Wizard.action_convert_location(self.test_parent_partner)

        # check if 'Parent Partner' creation successful and fields copied over
        wiz_parent = self.env["fsm.location"].search([("name", "=", "Parent Partner")])

        # check all children were assigned type 'other'
        for child in wiz_parent.child_ids:
            self.assertEqual(child.type, "other")
