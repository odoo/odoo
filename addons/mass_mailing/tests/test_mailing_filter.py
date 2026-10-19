# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mass_mailing.tests.common import MassMailCommon
from odoo.tests import tagged


@tagged('at_install', '-post_install')
class TestMailingFilter(MassMailCommon):
    """Unit tests for the `mailing.filter` (Dynamic List) model"""
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_compute_mailing_count(self):
        # Prepare
        res_partner_model_id = self.env['ir.model']._get('res.partner').id
        filter_1, filter_2 = self.env['mailing.filter'].create([
            {
                'name': 'LLN City',
                'mailing_domain': [('city', 'ilike', 'LLN')],
                'mailing_model_id': res_partner_model_id,
            },
            {
                'name': 'Email based',
                'mailing_domain': [('email', 'ilike', 'info@odoo.com')],
                'mailing_model_id': res_partner_model_id,
            }
        ])
        self.env['mailing.mailing'].create([
            {
                'subject': 'First subject',
                'mailing_model_id': res_partner_model_id,
                'mailing_filter_ids': filter_1 | filter_2
            },
            {
                'subject': 'Second subject',
                'mailing_model_id': res_partner_model_id,
                'mailing_filter_ids': filter_1
            }
        ])
        # Execute & assert
        self.assertEqual(2, filter_1.mailing_count)
        self.assertEqual(1, filter_2.mailing_count)
