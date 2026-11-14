# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestWebsiteImport(TransactionCase):

    def test_import_does_not_create_website(self):
        """ 'Create new values' must not create websites from an import file. """
        website_count = self.env['website'].search_count([])
        partner_count = self.env['res.partner'].search_count([])
        result = self.env['res.partner'].with_context(
            import_file=True,
            name_create_enabled_fields={'website_id': True},
        ).load(['name', 'website_id'], [['Import Partner', 'test-contact-import.org']])
        self.assertFalse(result['ids'])
        self.assertTrue(result['messages'])
        self.assertEqual(self.env['website'].search_count([]), website_count)
        self.assertEqual(self.env['res.partner'].search_count([]), partner_count)
