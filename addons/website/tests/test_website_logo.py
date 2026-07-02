# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import BinaryBytes


@tagged('post_install', '-at_install')
class TestWebsiteLogo(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.logo_v1 = BinaryBytes(b'fake-logo-bytes-v1')
        cls.logo_v2 = BinaryBytes(b'fake-logo-bytes-v2')
        cls.website = cls.env['website'].create({
            'name': 'Test Site',
            'logo': cls.logo_v1,
        })

    def _bound_logo(self, website):
        return self.env['ir.attachment'].search([
            ('res_model', '=', 'website'),
            ('res_field', '=', 'logo'),
            ('res_id', '=', website.id),
        ])

    def _media_logos(self, website):
        return self.env['ir.attachment'].search([
            ('res_model', '=', 'website'),
            ('res_field', '=', False),
            ('res_id', '=', website.id),
        ])

    def test_default_logo_not_mirrored(self):
        # create new website, since we want default logo to be set and tested
        website = self.env['website'].create({'name': 'Default Logo Site'})
        self.assertTrue(self._bound_logo(website), "bound logo expected for default")
        self.assertFalse(
            self._media_logos(website),
            "default placeholder must not produce a media-library row",
        )

    def test_custom_logo_mirrored(self):
        bound = self._bound_logo(self.website)
        mirrors = self._media_logos(self.website)
        self.assertEqual(len(mirrors), 1, "exactly one media-library row expected")
        self.assertEqual(mirrors.checksum, bound.checksum)
        self.assertEqual(bytes(mirrors.raw), bytes(bound.raw))

    def test_no_duplicate_on_same_bytes_write(self):
        self.website.logo = self.logo_v1
        self.assertEqual(len(self._media_logos(self.website)), 1)

    def test_replace_logo_keeps_previous(self):
        self.website.logo = self.logo_v2
        bound = self._bound_logo(self.website)
        mirrors = self._media_logos(self.website)
        self.assertEqual(len(mirrors), 2)
        self.assertIn(bound.checksum, mirrors.mapped('checksum'))
        self.assertEqual(
            {bytes(r) for r in mirrors.mapped('raw')},
            {b'fake-logo-bytes-v1', b'fake-logo-bytes-v2'},
        )
