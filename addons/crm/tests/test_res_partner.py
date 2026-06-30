from odoo.addons.crm.tests.common import TestCrmCommon
from odoo.tests import tagged, users


# This is explicit: we want CRM only check, to test base method
@tagged('res_partner', '-post_install', 'at_install')
class TestResPartner(TestCrmCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.contact_1_1, cls.contact_1_2 = cls.env['res.partner'].create([
            {
                'name': 'Philip J Fry Bouffe-tête',
                'email': 'bouffe.tete@test.example.com',
                'function': 'Bouffe-Tête',
                'lang': cls.lang_en.code,
                'phone': False,
                'parent_id': cls.contact_1.id,
                'is_company': False,
                'street': 'Same as Fry',
                'city': 'New York',
                'country_id': cls.env.ref('base.us').id,
                'zip': '54321',
            }, {
                'name': 'Philip J Fry Banjo',
                'email': 'banjo@test.example.com',
                'function': 'Being a banjo',
                'lang': cls.lang_en.code,
                'phone': False,
                'parent_id': cls.contact_1.id,
                'is_company': False,
                'street': 'Same as Fry',
                'city': 'New York',
                'country_id': cls.env.ref('base.us').id,
                'zip': '54321',
            }
        ])

        cls.test_leads = cls.env['crm.lead'].create([
            {
                'name': 'CompanyLead',
                'type': 'lead',
                'partner_id': cls.contact_company_1.id,
            }, {
                'name': 'ChildLead',
                'type': 'lead',
                'partner_id': cls.contact_1.id,
            }, {
                'name': 'GrandChildLead',
                'type': 'lead',
                'partner_id': cls.contact_1_1.id,
            }, {
                'name': 'GrandChildOpp',
                'type': 'opportunity',
                'partner_id': cls.contact_1_1.id,
            }, {
                'name': 'Nobody',
                'type': 'opportunity',
            },
        ])

    @users('user_sales_manager')
    def test_fields_opportunity_count(self):
        (
            contact_company_1, contact_1, contact_1_1, contact_1_2
        ) = (
            self.contact_company_1 + self.contact_1 + self.contact_1_1 + self.contact_1_2
        ).with_env(self.env)
        self.assertEqual(contact_company_1.opportunity_count, 4, 'Should contain own + children leads')
        self.assertEqual(contact_1.opportunity_count, 3, 'Should contain own + child leads')
        self.assertEqual(contact_1_1.opportunity_count, 2, 'Should contain own, aka 2')
        self.assertEqual(contact_1_2.opportunity_count, 0, 'Should contain own, aka none')
