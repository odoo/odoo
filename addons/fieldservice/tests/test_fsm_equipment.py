# Copyright (C) 2019 - TODAY, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import Form
from odoo.tests.common import TransactionCase


class FSMEquipment(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Equipment = cls.env["fsm.equipment"]
        cls.test_location = cls.env.ref("fieldservice.test_location")
        cls.test_territory = cls.env.ref("base_territory.test_territory")
        cls.test_branch = cls.env.ref("base_territory.test_branch")
        cls.test_district = cls.env.ref("base_territory.test_district")
        cls.test_region = cls.env.ref("base_territory.test_region")
        cls.current_location = cls.env.ref("fieldservice.location_1")

    def test_fsm_equipment(self):
        """Test createing new equipment
        - Default stage
        - Onchange location
        - Change stage
        """
        # Create an equipment
        view_id = "fieldservice.fsm_equipment_form_view"
        with Form(self.Equipment, view=view_id) as f:
            f.name = "Equipment 1"
            f.current_location_id = self.current_location
            f.location_id = self.test_location
        equipment = f.save()
        # Test onchange location
        self.assertEqual(self.test_territory, equipment.territory_id)
        self.assertEqual(self.test_branch, equipment.branch_id)
        self.assertEqual(self.test_district, equipment.district_id)
        self.assertEqual(self.test_region, equipment.region_id)
        # Test initial stage
        self.assertEqual(
            equipment.stage_id, self.env.ref("fieldservice.equipment_stage_1")
        )

        # Test change state
        equipment.next_stage()
        self.assertEqual(
            equipment.stage_id, self.env.ref("fieldservice.equipment_stage_2")
        )
        equipment.stage_id = self.env.ref("fieldservice.equipment_stage_3")
        equipment.next_stage()
        self.assertEqual(
            equipment.stage_id, self.env.ref("fieldservice.equipment_stage_3")
        )
        self.assertFalse(equipment.hide)  # hide as max stage
        equipment.stage_id = self.env.ref("fieldservice.equipment_stage_2")
        equipment.previous_stage()
        self.assertEqual(
            equipment.stage_id, self.env.ref("fieldservice.equipment_stage_1")
        )
        data = (
            self.env["fsm.equipment"]
            .with_user(self.env.user)
            .read_group(
                [("id", "=", equipment.id)],
                fields=["stage_id"],
                groupby="stage_id",
            )
        )
        self.assertTrue(data, "It should be able to read group")
