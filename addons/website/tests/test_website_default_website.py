from odoo.tests import TransactionCase, tagged


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

    def tearDown(self):
        """
        Clean up any websites created during tests and set back
        the initial website as the default one
        """
        super().tearDown()
        websites = self.Website.search([('id', '!=', '1')])
        for website in websites:
            # Top website is default and must be moved to be deleted
            website.sequence = 100
            website.unlink()

    def test_01_create_xmlid_when_missing(self):
        """
        Test that the function creates the ir.model.data record
        when it doesn't exist.
        """
        website = self.Website.create({'name': 'Test Website', 'sequence': 1})
        default_website_data = self.IrModelData.search([
            ('module', '=', 'website'),
            ('name', '=', 'default_website'),
            ('model', '=', 'website')
        ])
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
        new_website = self.Website.create({'name': 'New Website', 'sequence': 10})
        # The initial website should still be the default
        default_website_data = self.IrModelData.search([
            ('module', '=', 'website'),
            ('name', '=', 'default_website'),
            ('model', '=', 'website')
        ])
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
        default_website_data = self.IrModelData.search([
            ('module', '=', 'website'),
            ('name', '=', 'default_website'),
            ('model', '=', 'website')
        ])
        self.assertEqual(default_website_data.res_id, 1)

        # Create new website
        new_website = self.Website.create({'name': 'New Website', 'sequence': 1})
        # New website should now be the default
        self.assertEqual(
            default_website_data.res_id,
            new_website.id,
            "The XML ID should be updated to point to the website with lowest sequence"
        )
