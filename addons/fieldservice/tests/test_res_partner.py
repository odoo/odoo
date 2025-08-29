# Copyright (C) 2023, Brian McMaster
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class FSMResPartner(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.location_one = cls.env.ref("fieldservice.location_1")
        cls.location_one_partner = cls.location_one.partner_id
        cls.parent_partner = cls.env.ref("fieldservice.test_parent_partner")
        cls.sub_partner_1 = cls.env.ref("fieldservice.s1")
        cls.sub_partner_2 = cls.env.ref("fieldservice.s2")
        cls.loc_1 = cls.env["fsm.location"].create(
            {"name": "Test Location 1", "owner_id": cls.sub_partner_1.id}
        )
        cls.loc_2 = cls.env["fsm.location"].create(
            {"name": "Test Location 2", "owner_id": cls.sub_partner_2.id}
        )

    def test_res_partner_open_owned_locations(self):
        # Test with one owner location
        action = self.location_one_partner.action_open_owned_locations()
        self.assertEqual(action["res_id"], self.location_one.id)

        # Test with multiple owned locations
        expected_domain = [("id", "in", [self.loc_1.id, self.loc_2.id])]
        action = self.parent_partner.action_open_owned_locations()
        self.assertEqual(action["domain"], expected_domain)
