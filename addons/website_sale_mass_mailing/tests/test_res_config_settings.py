from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestResConfigSettings(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Website = cls.env['website']
        MailingList = cls.env['mailing.list']

        cls.mailing_list = MailingList.search([], limit=1)
        assert cls.mailing_list, "No mailing list found for the test."

        cls.site_one = Website.create({'name': 'Site 1'})
        cls.site_two = Website.create({'name': 'Site 2'})

        cls.site_one_settings = cls._create_settings_for_website(cls.site_one, False)
        cls.site_two_settings = cls._create_settings_for_website(cls.site_two, False)

    @classmethod
    def _create_settings_for_website(cls, website, enable_newsletter):
        """Create and execute settings for a given website."""
        settings = cls.env['res.config.settings'].with_context(website_id=website.id).create({
            'newsletter_id': cls.mailing_list.id,
            'is_newsletter_enabled': enable_newsletter,
            'website_id': website.id,
        })
        settings.execute()
        return settings

    def _get_newsletter_view_for_website(self, website_setting, website):
        """Return the newsletter view associated with a specific website."""
        website = website_setting.with_context(website_id=website.id).website_id
        return website.viewref('website_sale_mass_mailing.newsletter')

    def test_newsletter_enabled_per_website(self):
        """Test newsletter enablement per website and its effect on view activation."""
        # Ensure initial state: newsletter is disabled for both websites
        self.assertFalse(self.site_one_settings.is_newsletter_enabled)
        self.assertFalse(self.site_two_settings.is_newsletter_enabled)

        # Enable newsletter for site one
        self.site_one_settings.is_newsletter_enabled = True
        self.site_one_settings.execute()

        site_one_newsletter_view = self._get_newsletter_view_for_website(self.site_one_settings, self.site_one)
        self.assertTrue(site_one_newsletter_view.active, "Newsletter view should be active for Site One")
        self.assertTrue(self.site_one_settings.is_newsletter_enabled)
        self.assertFalse(self.site_two_settings.is_newsletter_enabled)

        # Enable newsletter for site two
        self.site_two_settings.is_newsletter_enabled = True
        self.site_two_settings.execute()

        site_two_newsletter_view = self._get_newsletter_view_for_website(self.site_two_settings, self.site_two)
        self.assertTrue(site_two_newsletter_view.active, "Newsletter view should be active for Site Two")
        self.assertTrue(self.site_two_settings.is_newsletter_enabled)
