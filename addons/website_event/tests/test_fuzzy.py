from datetime import datetime, timedelta

from odoo.http import request
from odoo.tests import tagged

from odoo.addons.http_routing.tests.common import MockRequest
from odoo.addons.website.tests.test_fuzzy import TestAutoComplete


@tagged('-at_install', 'post_install')
class TestWebsiteEventAutocomplete(TestAutoComplete):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.event = cls.env['event.event'].create({
            'name': "Latest Singing Event",
            'website_published': True,
            'date_begin': datetime.today() - timedelta(days=1),
            'date_end': datetime.today() + timedelta(days=1),
        })

    def test_autocomplete_search_for_multiple_spaces(self):
        """Tests that autocomplete handles multiple spaces in the search term correctly."""
        with MockRequest(self.env, website=self.website):
            options = {
                "allowFuzzy": True,
                "display_currency": request.website.company_id.currency_id.id,
                "displayDescription": True,
                "displayDetail": False,
                "displayExtraLink": True,
                "displayImage": True,
                "order": "name asc",
            }
            result = self.WebsiteController.autocomplete(
                search_type="all",
                term="latest   singing        event   ",
                max_nb_chars=75,
                options=options,
            )
            expected = self.WebsiteController.autocomplete(
                search_type="all",
                term="latest singing event",
                max_nb_chars=75,
                options=options,
            )
        self.assertEqual(result, expected)
