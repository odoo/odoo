from odoo.tests import common


class TestWebsiteDesign(common.TransactionCase):
    def setUp(self):
        Website = self.env['website']
        self.website = Website.create({
            'name': 'Test Website',
        })
        WebsiteDesign = self.env['website.design']
        self.website_design = WebsiteDesign.create({
            'website_id': self.website.id,
        })

    def test_01_compute_logo_height(self):
        # Check the computation of the logo height
        self.website_design.font__size__base = '1.5rem'
        self.assertEqual(self.website_design.forced_logo_height, 'null')
        self.assertEqual(self.website_design.logo__height, '3.25rem')

        self.website_design.forced_logo_height = '1.5rem'
        self.assertEqual(self.website_design.forced_logo_height, '1.5rem')
        self.assertEqual(self.website_design.logo__height, '1.5rem')
