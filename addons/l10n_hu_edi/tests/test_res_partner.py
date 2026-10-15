from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install_l10n', 'post_install', '-at_install')
class L10nHuEdiTestPartner(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partner_hu_company_a = cls.env['res.partner'].create({
            'name': 'HU Company A',
            'vat': 'HU12345678',
            'country_id': cls.env.ref('base.hu').id,
        })
        cls.partner_hu_company_b = cls.env['res.partner'].create({
            'name': 'HU Company B',
            'vat': '12345678-2-43',
            'country_id': cls.env.ref('base.hu').id,
        })
        cls.partner_hu_no_company_a = cls.env['res.partner'].create({
            'name': 'HU NO Company A',
            'country_id': cls.env.ref('base.hu').id,
        })
        cls.partner_hu_no_company_b = cls.env['res.partner'].create({
            'name': 'HU NO Company B',
            'parent_id': cls.partner_hu_company_b.id,
            'vat': '12345678-2-43',
            'country_id': cls.env.ref('base.hu').id,
        })

    def test_is_company_hu(self):
        self.assertTrue(self.partner_hu_company_a.is_company)
        self.assertTrue(self.partner_hu_company_b.is_company)
        self.assertFalse(self.partner_hu_no_company_a.is_company)
        self.assertFalse(self.partner_hu_no_company_b.is_company)
