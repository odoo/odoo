# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nPa(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('pa')
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data['default_journal_sale'].l10n_latam_use_documents = True

    def test_numbering_per_document_type(self):
        first_invoice = self._create_invoice(l10n_latam_document_number='00000042', post=True)
        eight_digit_invoice = self._create_invoice(name='FE 00000050', post=True)
        refund = self._create_invoice(move_type='out_refund', post=True)
        second_invoice = self._create_invoice(post=True)
        third_invoice = self._create_invoice(post=True)
        self.assertEqual(
            [first_invoice.name, eight_digit_invoice.name, second_invoice.name, third_invoice.name, refund.name],
            ['FE 0000000042', 'FE 00000050', 'FE 0000000051', 'FE 0000000052', 'NCG 0000000001'],
        )
        for number in ('12345678901', '12A'):
            with self.subTest(number=number), self.assertRaisesRegex(UserError, "at most 10 digits"):
                self.env.ref('l10n_pa.document_type_01')._format_document_number(number)

    def test_taxpayer_type_from_ruc_format(self):
        partner = self.env['res.partner'].create({'name': 'Ana Pérez', 'country_id': self.env.ref('base.pa').id})
        for vat, expected_type in (
            ('8-100-678', '1'),
            ('13-1-2', '1'),
            ('PE-15-200', '1'),
            ('E-8-157481', '1'),
            ('N-19-1234', '1'),
            ('3-NT-3-33', '1'),
            ('14-100-678', '2'),
            (False, False),
        ):
            with self.subTest(vat=vat):
                partner.vat = vat
                self.assertEqual(partner.l10n_pa_taxpayer_type, expected_type)
        partner.write({'vat': '155986022-2-2019', 'country_id': self.env.ref('base.us').id})
        self.assertFalse(partner.l10n_pa_taxpayer_type)
