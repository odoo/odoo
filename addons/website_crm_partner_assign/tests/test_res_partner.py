from odoo.addons.crm.tests.test_res_partner import TestResPartner
from odoo.tests import tagged, users
from odoo.tests.common import warmup


@tagged('res_partner', 'post_install', '-at_install')
class TestResPartnerWAssign(TestResPartner):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.test_leads[3:].write({
            'partner_assigned_id': cls.contact_1_2.id,
        })

    @users('user_sales_manager')
    @warmup
    def test_fields_opportunity_count(self):
        # this query counter is there to ensure prefetching works and we don't
        # browse partner sequentially
        with self.assertQueryCount(4):
            (
                contact_company_1, contact_1, contact_1_1, contact_1_2
            ) = (
                self.contact_company_1 + self.contact_1 + self.contact_1_1 + self.contact_1_2
            ).with_env(self.env)
            self.assertEqual(
                contact_company_1.opportunity_count, 5,
                'Should contain own + children leads / assigned')
            self.assertEqual(
                contact_1.opportunity_count, 4,
                'Should contain own + child leads / assigned')
            self.assertEqual(
                contact_1_1.opportunity_count, 2,
                'Should contain own, aka 2')
            self.assertEqual(
                contact_1_2.opportunity_count, 2,
                'Should contain own, aka assigned')
