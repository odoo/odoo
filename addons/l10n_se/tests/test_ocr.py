# Part of Odoo. See LICENSE file for full copyright and licensing details.
from stdnum import luhn

from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import SeAccountTestCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestSeOcr(SeAccountTestCommon):
    """Swedish OCR references (Bankgirot): generation on customer invoices, validation on vendor bills."""

    def test_ocr_levels(self):
        move = self._invoice('out_invoice', self._tax('sale_tax_25_goods'))
        # Values computed independently with stdnum (Luhn) per Bankgirot's OCR levels
        self.assertEqual(move._get_invoice_reference_se_ocr2('1234'), '12344')
        self.assertEqual(move._get_invoice_reference_se_ocr3('1234'), '123463')
        move.journal_id.l10n_se_invoice_ocr_length = 8
        self.assertEqual(move._get_invoice_reference_se_ocr4('123'), '00001230')

    def test_ocr3_length_digit_units(self):
        """From 10 digits the length digit is the units digit of the total length (Bankgirot)."""
        move = self._invoice('out_invoice', self._tax('sale_tax_25_goods'))
        reference = move._get_invoice_reference_se_ocr3('12345678')
        self.assertEqual(reference, '1234567806')
        self.assertEqual(reference[-2], str(len(reference) % 10))

    def test_ocr4_too_long(self):
        move = self._invoice('out_invoice', self._tax('sale_tax_25_goods'))
        move.journal_id.l10n_se_invoice_ocr_length = 6
        with self.assertRaises(UserError):
            move._get_invoice_reference_se_ocr4('1234567')

    def test_journal_ocr_length_minimum(self):
        journal = self.company_data['default_journal_sale']
        with mute_logger('odoo.sql_db'), self.assertRaises(Exception), self.env.cr.savepoint():
            journal.l10n_se_invoice_ocr_length = 5
            journal.flush_recordset()

    def test_invoice_reference_on_post(self):
        """The journal's OCR model sets a valid OCR as payment reference when posting."""
        journal = self.company_data['default_journal_sale']
        journal.write({'invoice_reference_model': 'se_ocr3', 'invoice_reference_type': 'invoice'})
        move = self._invoice('out_invoice', self._tax('sale_tax_25_goods'))
        reference = move.payment_reference
        self.assertTrue(reference.startswith(str(move.id)))
        self.assertTrue(luhn.is_valid(reference))
        self.assertEqual(reference[-2], str(len(reference) % 10))

    def test_vendor_ocr_validation(self):
        vendor = self.env['res.partner'].create({
            'name': 'OCR-leverantör AB',
            'country_id': self.env.ref('base.se').id,
            'l10n_se_check_vendor_ocr': True,
        })
        tax = self._tax('purchase_tax_25_goods')
        # An invalid OCR is rejected as soon as it is entered
        with self.assertRaises(ValidationError):
            self._create_invoice(
                move_type='in_invoice', partner_id=vendor.id, payment_reference='1235',
                invoice_line_ids=[self._prepare_invoice_line(price_unit=100, tax_ids=tax)],
            )
        # A bill from a vendor requiring OCR cannot be posted without one
        bill = self._create_invoice(
            move_type='in_invoice', partner_id=vendor.id,
            invoice_line_ids=[self._prepare_invoice_line(price_unit=100, tax_ids=tax)],
        )
        bill.payment_reference = False
        with self.assertRaises(ValidationError):
            bill.action_post()
        # A valid OCR is accepted
        bill.payment_reference = '12344'
        bill.action_post()
        self.assertEqual(bill.state, 'posted')

    def test_vendor_without_ocr_requirement(self):
        bill = self._invoice('in_invoice', self._tax('purchase_tax_25_goods'))
        self.assertEqual(bill.state, 'posted')

    def test_vendor_ocr_on_contact_person(self):
        """The OCR requirement is set on the vendor company and applies to bills addressed to its contacts."""
        vendor = self.env['res.partner'].create({
            'name': 'OCR-leverantör AB', 'is_company': True,
            'country_id': self.env.ref('base.se').id, 'l10n_se_check_vendor_ocr': True,
        })
        contact = self.env['res.partner'].create({'name': 'Kontaktperson', 'parent_id': vendor.id})
        with self.assertRaises(ValidationError):
            self._create_invoice(
                move_type='in_invoice', partner_id=contact.id, payment_reference='1235',
                invoice_line_ids=[self._prepare_invoice_line(price_unit=100, tax_ids=self._tax('purchase_tax_25_goods'))],
            )

    def test_customer_ocr_same_for_all_contacts(self):
        """A customer-based OCR reference is the same whichever contact the invoice is addressed to."""
        customer = self.env['res.partner'].create({'name': 'Kund AB', 'is_company': True, 'ref': '4711',
                                                   'country_id': self.env.ref('base.se').id})
        contact = self.env['res.partner'].create({'name': 'Kontaktperson', 'parent_id': customer.id})
        tax = self._tax('sale_tax_25_goods')
        to_company = self._invoice('out_invoice', tax, partner=customer)
        to_contact = self._invoice('out_invoice', tax, partner=contact)
        self.assertEqual(to_company._get_invoice_reference_se_ocr3_partner(), to_contact._get_invoice_reference_se_ocr3_partner())
        self.assertTrue(to_company._get_invoice_reference_se_ocr3_partner().startswith('4711'))
