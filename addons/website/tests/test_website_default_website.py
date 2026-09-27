from unittest.mock import patch

from odoo.fields import Domain
from odoo.tests import TransactionCase, tagged

from odoo.addons.website.models.website import Website


@tagged("post_install", "-at_install")
class TestWebsiteDefaultWebsiteConsistency(TransactionCase):
    """
    Test the _ensure_default_website_consistency method which ensures that
    the 'base.default_website' XML ID always points to the first website
    ordered by sequence, then id.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Website = cls.env["website"]
        cls.IrModelData = cls.env["ir.model.data"]
        cls.DefaultWebsiteDomain = Domain(
            [
                ("module", "=", "base"),
                ("name", "=", "default_website"),
                ("model", "=", "website"),
            ],
        )

    def test_01_ensure_default_creates_xmlid_when_missing(self):
        """
        Test that the function creates ir.model.data record if it is missing.
        """
        # Remove the default_website XML ID if existing (it should exist)
        default_website_data = self.IrModelData.search(self.DefaultWebsiteDomain)
        self.assertEqual(
            len(default_website_data),
            1,
            "Should have exactly one default_website XML ID",
        )
        default_website_data.unlink()

        # Check that the default_website XML ID has been removed
        default_website_data = self.IrModelData.search(self.DefaultWebsiteDomain)
        self.assertEqual(
            len(default_website_data),
            0,
            "The default_website XML ID should have been removed",
        )

        # Check that when a new website is created, default_website XML ID
        # is created again
        website = self.Website.create({"name": "Test Website", "sequence": 1})
        default_website_data = self.IrModelData.search(self.DefaultWebsiteDomain)
        self.assertEqual(
            len(default_website_data),
            1,
            "Should create exactly one default_website XML ID",
        )
        self.assertEqual(
            default_website_data.res_id,
            website.id,
            "The XML ID should point to the first website by sequence",
        )

    def test_02_ensure_default_on_sequence_change(self):
        """
        Test that when a website with a lower sequence is dragged,
        on top, the default_website XML ID is updated to point to it.
        """
        initial_default_website = self.env.ref("base.default_website")

        # Create new website
        new_website = self.Website.create(
            {"name": "New Website", "sequence": initial_default_website.sequence + 1},
        )

        # The initial website is still default
        self.assertEqual(
            initial_default_website,
            self.env.ref("base.default_website"),
            "The default website should not have changed",
        )

        # Move new website on top
        new_website.sequence = initial_default_website.sequence - 1

        # New website should now be the default
        self.assertNotEqual(
            initial_default_website,
            self.env.ref("base.default_website"),
            "The default website should have changed",
        )
        self.assertEqual(
            self.env.ref("base.default_website"),
            new_website,
            "The default website should be the one with lowest sequence",
        )

    def test_03_ensure_default_on_create(self):
        """
        Test that _ensure_default_website_consistency is called
        automatically when creating a new website.
        """
        initial_default_website = self.env.ref("base.default_website")

        # Create new website
        new_website = self.Website.create(
            {"name": "New Website", "sequence": initial_default_website.sequence - 1},
        )

        # New website should now be the default
        self.assertNotEqual(
            initial_default_website,
            self.env.ref("base.default_website"),
            "The default website should have changed",
        )
        self.assertEqual(
            self.env.ref("base.default_website"),
            new_website,
            "The default website should be the one with lowest sequence",
        )

    def test_04_ensure_default_moves_settings_when_needed(self):
        """
        Test that _ensure_default_website_consistency moves the settings listed
        in SETTINGS_TO_TRANSFER_TO_NEW_DEFAULT_WEBSITE when they are present on
        the old default website and not on the new one.
        """
        initial_default_website = self.env.ref("base.default_website")

        # Settings to be copied depend on which modules are actually installed.
        # To make sure that at least one setting is present when this test is
        # executed, 'google_analytics_key' is added to the list of settings to
        # transfer.
        initial_default_website.write({"google_analytics_key": "examplekey"})
        with patch.object(Website, '_get_settings_to_copy_onto_new_default_website', return_value=['google_analytics_key']):
            settings_to_be_copied = [
                s
                for s in self.Website._get_settings_to_copy_onto_new_default_website()
                if s in self.Website._fields
            ]

            # Create new default website
            new_website = self.Website.create(
                {"name": "New Website", "sequence": initial_default_website.sequence - 1},
            )

        self.assertTrue(len(settings_to_be_copied) > 0, "settings_to_be_copied should contain at least an element")

        # New website should now be the default
        self.assertNotEqual(
            initial_default_website,
            self.env.ref("base.default_website"),
            "The default website should have changed",
        )
        self.assertEqual(
            self.env.ref("base.default_website"),
            new_website,
            "The default website should be the one with lowest sequence",
        )

        # Verify that the settings have been transferred
        for s in settings_to_be_copied:
            self.assertEqual(new_website[s], initial_default_website[s])
