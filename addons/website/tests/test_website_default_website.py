from odoo.tests import TransactionCase, tagged
from odoo.addons.website.models.website import SETTINGS_TO_TRANSFER_TO_NEW_DEFAULT_WEBSITE
from odoo.fields import Domain


@tagged('post_install', '-at_install')
class TestWebsiteDefaultWebsiteConsistency(TransactionCase):
    """
    Test the _ensure_default_website_consistency method which ensures that
    the 'website.default_website' XML ID always points to the first website
    ordered by sequence, then id.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Website = cls.env['website']
        cls.IrModelData = cls.env['ir.model.data']
        cls.DefaultWebsiteDomain = Domain(
            [
                ('module', '=', 'website'),
                ('name', '=', 'default_website'),
                ('model', '=', 'website')
        ])

    def test_01_ensure_default_creates_xmlid_when_missing(self):
        """
        Test that the function creates ir.model.data record if it is missing.
        """
        # Remove the default_website XML ID if existing (it should exist)
        default_website_data = self.IrModelData.search(self.DefaultWebsiteDomain)
        if len(default_website_data):
            default_website_data.unlink()

        # Check that the default_website XML ID has been removed
        default_website_data = self.IrModelData.search(self.DefaultWebsiteDomain)
        self.assertEqual(len(default_website_data), 0, "The default_website XML ID should have been removed")

        # Check that when a new website is created, default_website XML ID
        # is created again
        website = self.Website.create({'name': 'Test Website', 'sequence': 1})
        default_website_data = self.IrModelData.search(self.DefaultWebsiteDomain)
        self.assertEqual(len(default_website_data), 1, "Should create exactly one default_website XML ID")
        self.assertEqual(
            default_website_data.res_id,
            website.id,
            "The XML ID should point to the first website by sequence"
        )

    def test_02_ensure_default_on_sequence_change(self):
        """
        Test that when a website with a lower sequence is dragged,
        on top, the default_website XML ID is updated to point to it.
        """
        # Create new website
        new_website = self.Website.create({'name': 'New Website', 'sequence': 50})
        # The initial website should still be the default
        default_website_data = self.IrModelData.search(self.DefaultWebsiteDomain)
        self.assertEqual(default_website_data.res_id, 1)

        # Move new website on top
        new_website.sequence = 1
        # New website should now be the default
        self.assertEqual(
            default_website_data.res_id,
            new_website.id,
            "The XML ID should be updated to point to the website with lowest sequence"
        )

    def test_03_ensure_default_on_create(self):
        """
        Test that _ensure_default_website_consistency is called
        automatically when creating a new website.
        """
        # The initial website should be the default
        default_website_data = self.IrModelData.search(self.DefaultWebsiteDomain)
        self.assertEqual(default_website_data.res_id, 1)

        # Create new website
        new_website = self.Website.create({'name': 'New Website', 'sequence': 1})
        # New website should now be the default
        self.assertEqual(
            default_website_data.res_id,
            new_website.id,
            "The XML ID should be updated to point to the website with lowest sequence"
        )

    def test_04_ensure_default_moves_settings_when_needed(self):
        """
        Test that _ensure_default_website_consistency moves the settings listed
        in SETTINGS_TO_TRANSFER_TO_NEW_DEFAULT_WEBSITE when they are present on
        the old default website and not on the new one.
        """
        default_website_data = self.IrModelData.search(self.DefaultWebsiteDomain)
        default_website = self.Website.search([('id', '=', default_website_data.res_id)])
        # Settings to be transferred depend on which modules are actually
        # installed. The list settings_to_be_transferred may even be empty.
        settings_to_be_transferred = [
            s for s in SETTINGS_TO_TRANSFER_TO_NEW_DEFAULT_WEBSITE if s in self.Website._fields
        ]
        # Create new default website
        new_website = self.Website.create({'name': 'New Website', 'sequence': 1})
        # Verify that the settings have been transferred
        for s in settings_to_be_transferred:
            self.assertEqual(new_website[s], default_website[s])
