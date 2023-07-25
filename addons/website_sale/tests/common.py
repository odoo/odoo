from odoo.tests.common import HttpCase

class TestWebsiteSaleCommon(HttpCase):

    def setUp(self):
        super(TestWebsiteSaleCommon, self).setUp()
        # Update website pricelist to ensure currency is same as env.company
        website = self.env['website'].get_current_website()
        pricelist = website.get_current_pricelist()
        pricelist.write({'currency_id': self.env.company.currency_id.id})
