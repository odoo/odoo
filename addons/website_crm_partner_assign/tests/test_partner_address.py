from odoo.addons.portal.tests.test_addresses import TestPortalAddresses
from odoo.addons.website_crm_partner_assign.tests.common import patch_geo_find
from odoo.http import Request


class TestPortalAddressGeolocation(TestPortalAddresses):
    """Test the geolocation of partner addresses in the portal."""
    def setUp(self):
        super().setUp()
        self.startPatcher(patch_geo_find())

    def test_geo_update_on_address_change(self):
        """Test that updating partner address via website recomputes coordinates."""
        self.authenticate(self.portal_user.login, self.portal_user.login)
        csrf_token = Request.csrf_token(self)

        # Assign a grade to the portal user partner to ensure geolocation is triggered
        grade = self.env["res.partner.grade"].create({"name": "Gold partner"})
        portal_user_partner = self.portal_user.partner_id
        portal_user_partner.write({
            "city": "Wavre",
            "country_id": self.env.ref("base.be").id,
            "grade_id": grade.id,
        })
        # Trigger geolocation update as to recompute coordinates partner must have previously geo-located 
        portal_user_partner.with_context(force_geo_localize=True).geo_localize()

        # Submit the address update via the website form
        response = self._submit_address_values({
            'city': 'Gandhinagar',
            'country_id': self.env.ref('base.in').id,
            'csrf_token': csrf_token,
            'email': 'p.p@example.com',
            'force_geo_localize': True,  # You can also test with False here if needed
            'name': 'portal_user (base.group_portal)',
            'partner_id': self.portal_user.partner_id.id,
            'phone': '+91 12345 67890',
            'state_id': self.env.ref('base.state_in_gj').id,
            'street': '1',
            'zip': '382010',
        })
        self.assertEqual(response, {'redirectUrl': '/my/addresses'})

        # Verify that coordinates were updated correctly
        self.assertEqual(portal_user_partner.partner_latitude, 23.1933118)
        self.assertEqual(portal_user_partner.partner_longitude, 72.6348905)
