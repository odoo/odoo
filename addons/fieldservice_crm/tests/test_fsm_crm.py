from odoo.tests import common


class TestFieldserviceCrm(common.TransactionCase):
    def test_fieldservicecrm(self):
        location_1 = self.env["fsm.location"].create(
            {
                "name": "Summer's House",
                "owner_id": self.env["res.partner"]
                .create({"name": "Summer's Parents"})
                .id,
            }
        )
        crm_1 = self.env["crm.lead"].create(
            {
                "name": "Test CRM",
                "fsm_location_id": location_1.id,
            }
        )
        self.env["fsm.order"].create(
            {
                "location_id": location_1.id,
                "opportunity_id": crm_1.id,
            }
        )
        crm_1._compute_fsm_order_count()
        self.assertEqual(crm_1.fsm_order_count, 1)

        location_1._compute_opportunity_count()
        self.assertEqual(location_1.opportunity_count, 1)
