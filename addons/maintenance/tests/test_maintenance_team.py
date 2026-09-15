from odoo.tests import Form, TransactionCase


class TestMaintenanceOrderTeam(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Team = cls.env["team.team"]
        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].create(
            {"name": "Probe Other Company"}
        )
        cls.default_team = Team.search(
            [("use_maintenance", "=", True), ("company_id", "=", cls.company.id)],
            limit=1,
        ) or Team.create(
            {
                "use_maintenance": True,
                "name": "Probe Default Team",
                "company_id": cls.company.id,
            }
        )
        cls.asset_team = Team.create(
            {
                "use_maintenance": True,
                "name": "Probe Asset Team",
                "company_id": cls.company.id,
            }
        )
        cls.other_team = Team.create(
            {
                "use_maintenance": True,
                "name": "Probe Other Company Team",
                "company_id": cls.other_company.id,
            }
        )
        cls.asset = cls.env["resource.asset"].create(
            {
                "name": "Probe Asset",
                "kind_id": cls.env.ref("resource_asset.kind_equipment").id,
                "maintenance_team_id": cls.asset_team.id,
            }
        )

    def test_a_code_path_create_takes_the_asset_team(self):
        order = self.env["maintenance.order"].create(
            {"name": "Probe order", "resource_ids": self.asset.resource_id.ids}
        )
        self.assertEqual(order.maintenance_team_id, self.asset_team)

    def test_a_create_without_resources_takes_the_default_team(self):
        order = self.env["maintenance.order"].create({"name": "Probe order"})
        self.assertEqual(order.maintenance_team_id, self.default_team)

    def test_an_explicit_team_is_kept(self):
        order = self.env["maintenance.order"].create(
            {
                "name": "Probe order",
                "resource_ids": self.asset.resource_id.ids,
                "maintenance_team_id": self.default_team.id,
            }
        )
        self.assertEqual(order.maintenance_team_id, self.default_team)

    def test_the_form_path_still_takes_the_asset_team(self):
        form = Form(self.env["maintenance.order"])
        form.name = "Probe order"
        form.resource_ids.add(self.asset.resource_id)
        self.assertEqual(form.save().maintenance_team_id, self.asset_team)

    def test_the_default_team_is_the_order_company_s(self):
        order = (
            self.env["maintenance.order"]
            .with_company(self.company)
            .create({"name": "Probe order", "company_id": self.other_company.id})
        )
        self.assertEqual(order.maintenance_team_id, self.other_team)
