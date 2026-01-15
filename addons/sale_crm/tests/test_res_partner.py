from odoo.addons.crm.tests.common import TestCrmCommon
from odoo.tests import tagged, users


@tagged('res_partner', 'post_install', '-at_install')
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

        cls.test_product = cls.env['product.template'].create({
            'list_price': 100.0,
            'name': 'Test product1',
        })
        cls.test_pricelist = cls.env['product.pricelist'].create({
            'currency_id': cls.env.ref('base.USD').id,
            'name': 'My',
        })

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

        cls.test_so = cls.env['sale.order'].create([
            {
                'partner_id': cls.contact_company_1.id,
                'pricelist_id': cls.test_pricelist.id,
                'order_line': [
                    (0, 0, {
                        'product_id': cls.test_product.product_variant_id.id,
                    })
                ],
            }, {
                'partner_id': cls.contact_1.id,
                'pricelist_id': cls.test_pricelist.id,
                'order_line': [
                    (0, 0, {
                        'product_id': cls.test_product.product_variant_id.id,
                    })
                ],
            },
        ])

    @users('user_sales_manager')
    def test_application_stat_info(self):
        (
            contact_company_1, contact_1, contact_1_1, contact_1_2
        ) = (
            self.contact_company_1 + self.contact_1 + self.contact_1_1 + self.contact_1_2
        ).with_env(self.env)
        self.assertEqual(contact_company_1.opportunity_count, 4, 'Should contain own + children leads')
        self.assertEqual(contact_1.opportunity_count, 3, 'Should contain own + child leads')
        self.assertEqual(contact_1_1.opportunity_count, 2, 'Should contain own, aka 2')
        self.assertEqual(contact_1_2.opportunity_count, 0, 'Should contain own, aka none')

        for partner, expected in zip(
            (contact_company_1, contact_1, contact_1_1, contact_1_2),
            (
                [{'iconClass': 'fa-star', 'label': 'Opportunities', 'value': 4, 'tagClass': 'o_tag_color_8'},
                 {'iconClass': 'fa-usd', 'label': 'Sale Orders', 'value': 2, 'tagClass': 'o_tag_color_2'}],
                [{'iconClass': 'fa-star', 'label': 'Opportunities', 'value': 3, 'tagClass': 'o_tag_color_8'},
                 {'iconClass': 'fa-usd', 'label': 'Sale Orders', 'value': 1, 'tagClass': 'o_tag_color_2'}],
                [{'iconClass': 'fa-star', 'label': 'Opportunities', 'value': 2, 'tagClass': 'o_tag_color_8'}],
                False,
            ),
            strict=True,
        ):
            with self.subTest(pname=partner.name):
                self.assertEqual(partner.application_statistics, expected)
