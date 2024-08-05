from odoo.tests.common import TransactionCase


class TestSaleFlow(TransactionCase):
    ''' Test running at-install to test marketing_campaign.'''

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_preview(self):
        ''' Test 'Preview' button, it should open a public URL.'''

        campaign = self.browse_ref('marketing_card.card_campaign_campaign_1')

        # Test that a preview image has been generated
        self.assertTrue(campaign.image_preview)

        # Test that a preview image has been generated
        url = campaign.action_preview()['url']
        self.assertTrue(url)

        # Test the preview page
        # page = self.url_open(url)
        # self.assertIn(page, 'Share the news with your community')
        # self.assertIn(page, 'That xxx will help ')
