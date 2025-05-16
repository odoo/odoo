from odoo.tests import TransactionCase, tagged

from odoo.addons.http_routing.tests.common import MockRequest
from odoo.addons.website_customer.controllers.main import WebsiteCustomer


@tagged('-at_install', 'post_install')
class TestCustomerFilters(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partner_AB = cls.env['res.partner'].create({'name': "Partner AB"})
        cls.tag_A, cls.tag_B, cls.tag_C = cls.env['res.partner.tag'].create([
            {'name': "Tag A"},
            {'name': "Tag B"},
            {'name': "Tag C", 'website_published': False},
        ])
        company_data = {
            'assigned_partner_id': cls.partner_AB.id,
            'website_published': True,
        }
        cls.company_A, cls.company_B, cls.company_C = cls.env['res.partner'].create([
            {
                'name': "Company A",
                **company_data,
                'website_tag_ids': [cls.tag_A.id, cls.tag_B.id],
            },
            {
                'name': "Company B",
                **company_data,
                'website_tag_ids': [cls.tag_B.id],
            },
            {
                'name': "Company C",
                **company_data,
                'website_tag_ids': [cls.tag_C.id],
            },
        ])
        cls.websiteCustomerController = WebsiteCustomer()
        cls.slug = cls.env['ir.http']._slug
        cls.website = cls.env.ref('base.default_website')

    def _get_filtered_partners(self, tag="", search=""):
        partners = None
        with MockRequest(self.env, website=self.website) as request:
            def fake_render(_, values):
                nonlocal partners
                partners = values['partners']

            request.render = fake_render
            self.websiteCustomerController.customers(tag=tag, search=search)
        return partners

    def test_filter_without_tag_and_search(self):
        partners = self._get_filtered_partners()
        self.assertCountEqual(
            partners.ids,
            (self.company_A | self.company_B | self.company_C).ids,
            "No tag and search filter: all published companies must be returned",
        )

    def test_filter_with_tag_A(self):
        partners = self._get_filtered_partners(tag=self.slug(self.tag_A))
        self.assertEqual(
            partners.ids,
            self.company_A.ids,
            "Tag A filter: only Company A must be returned",
        )

    def test_filter_with_tag_B(self):
        partners = self._get_filtered_partners(tag=self.slug(self.tag_B))
        self.assertCountEqual(
            partners.ids,
            (self.company_A | self.company_B).ids,
            "Tag B filter: Companies A & B must be returned",
        )

    def test_filter_with_search(self):
        partners = self._get_filtered_partners(search="Company A")
        self.assertEqual(
            partners.ids,
            self.company_A.ids,
            "Search 'Company A': only Company A must be returned",
        )

    def test_filter_with_search_and_tag(self):
        partners = self._get_filtered_partners(
            tag=self.slug(self.tag_A), search="Company",
        )
        self.assertEqual(
            partners.ids,
            self.company_A.ids,
            "Tag A + Search 'Company': only Company A must be returned",
        )

    def test_filter_with_multiple_tags(self):
        """Filtering by Tag A and Tag B (OR) returns Companies A and B."""
        partners = self._get_filtered_partners(
            tag=f"{self.slug(self.tag_A)},{self.slug(self.tag_B)}",
        )
        self.assertCountEqual(
            partners.ids,
            (self.company_A | self.company_B).ids,
            "Multi-tag filter: Companies A & B must be returned",
        )

    def test_filter_with_multiple_tags_and_search(self):
        partners = self._get_filtered_partners(
            tag=f"{self.slug(self.tag_A)},{self.slug(self.tag_B)}", search="Company",
        )
        self.assertCountEqual(
            partners.ids,
            (self.company_A | self.company_B).ids,
            "Tag A + Tag B + Search 'Company': Company A & B must be returned",
        )

    def test_filter_with_unpublished_tag(self):
        """
        Passing an unpublished tag slug is silently ignored; all published
        partners are returned.
        """
        partners = self._get_filtered_partners(tag=self.slug(self.tag_C))
        self.assertCountEqual(
            partners.ids,
            (self.company_A | self.company_B | self.company_C).ids,
            "Unpublished tag filter should be ignored; all published companies must be returned",
        )

    def test_filter_with_tag_A_and_unpublished_tag_C(self):
        partners = self._get_filtered_partners(
            tag=f"{self.slug(self.tag_A)},{self.slug(self.tag_C)}",
        )
        self.assertEqual(
            partners.ids,
            self.company_A.ids,
            "Tag A + Unpublished Tag C filter: only Company A must be returned",
        )
