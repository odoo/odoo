from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "partner_scoring_crm")
class TestLeadTier(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Tier = cls.env["partner.tier"]
        Tier.search([]).write({"active": False})
        cls.low = Tier.create({"name": "Lead Low", "min_value": 0.0, "max_value": 0.0})
        cls.customer = cls.env["res.partner"].create(
            {"name": "Lead Customer", "is_company": True}
        )
        cls.customer._score_refresh()

    def test_a_lead_carries_the_customers_tier(self):
        lead = self.env["crm.lead"].create(
            {"name": "Tiered Lead", "partner_id": self.customer.id}
        )
        self.assertEqual(lead.tier_id, self.low)
        self.assertIn(
            lead.tier_id,
            self.env["crm.lead"].search([("tier_id", "=", self.low.id)]).tier_id,
        )

    def test_the_tier_is_a_predictive_scoring_feature(self):
        field = self.env.ref("partner_scoring_crm.frequency_field_tier_id").field_id
        self.assertEqual((field.model, field.name), ("crm.lead", "tier_id"))
        self.env["ir.config_parameter"].sudo().set_param("crm.pls_fields", "tier_id")
        self.assertIn("tier_id", self.env["crm.lead"]._pls_get_safe_fields())
