# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestResPartnerGrade(TransactionCase):

    def test_website_url_unsaved(self):
        """An unsaved grade must not be slugged."""
        self.assertEqual(self.env['res.partner.grade'].new({'name': 'Gold'}).website_url, '#')
        grade = self.env['res.partner.grade'].create({'name': 'Gold'})
        self.assertEqual(grade.website_url, f"/partners/grade/{self.env['ir.http']._slug(grade)}")
