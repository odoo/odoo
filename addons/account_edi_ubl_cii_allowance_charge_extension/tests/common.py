import base64
from freezegun import freeze_time

from odoo import fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAllowanceChargeCommon(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        # Regular Percentage Tax
        cls.tax_20 = cls.env['account.tax'].create({
            'name': 'tax_20',
            'amount_type': 'percent',
            'amount': 20,
            'type_tax_use': 'sale',
        })

        # Fixed Charge
        cls.fixed_charge = cls.env['account.tax'].create({
            'name': 'Fixed Charge',
            'amount_type': 'fixed',
            'amount': 50,
            'type_tax_use': 'sale',
            'ubl_cii_type': 'allowance_charge',
            'ubl_cii_charge_reason_code': 'AA',
        })

        # Line Discount Allowance
        cls.line_discount_allowance = cls.env['account.tax'].create({
            'name': 'Line Discount Allowance',
            'amount_type': 'percent',
            'amount': -5.0,
            'type_tax_use': 'sale',
            'ubl_cii_type': 'allowance_charge',
            'ubl_cii_allowance_reason_code': '95',
            'ubl_cii_allowance_charge_reason': 'Line Discount Allowance Reason',
        })

        # Variable Allowance (Special Rebate)
        cls.rebate_allowance = cls.env['account.tax'].create({
            'name': 'Special Rebate Allowance',
            'amount_type': 'percent',
            'amount': -15.0,
            'type_tax_use': 'sale',
            'ubl_cii_type': 'allowance_charge',
            'ubl_cii_allowance_reason_code': '100',
            'ubl_cii_allowance_charge_reason': 'Special Rebate',
        })

        # Variable Charge (Rents and Leases)
        cls.rent_and_lease_charge = cls.env['account.tax'].create({
            'name': 'Rent and Lease Charge',
            'amount_type': 'percent',
            'amount': 5.0,
            'type_tax_use': 'sale',
            'ubl_cii_type': 'allowance_charge',
            'ubl_cii_charge_reason_code': 'AEF',
            'ubl_cii_allowance_charge_reason': 'Rents and Leases',
        })

        cls.move_template = cls.env['mail.template'].create({
            'auto_delete': True,
            'body_html': '<p>TemplateBody for <t t-out="object.name"></t><t t-out="object.invoice_user_id.signature or \'\'"></t></p>',
            'description': 'Sent to customers with their invoices in attachment',
            'email_from': "{{ (object.invoice_user_id.email_formatted or user.email_formatted) }}",
            'model_id': cls.env['ir.model']._get_id('account.move'),
            'name': "Invoice: Test Sending",
            'partner_to': "{{ object.partner_id.id }}",
            'subject': "{{ object.company_id.name }} Invoice (Ref {{ object.name or 'n/a' }})",
            'report_template_ids': [(4, cls.env.ref('account.account_invoices').id)],
            'lang': "{{ object.partner_id.lang }}",
        })

    @classmethod
    def setup_company_data(cls, company_name, chart_template=None, **kwargs):
        eur = cls.env.ref('base.EUR')
        if not eur.active:
            eur.active = True
        res = super().setup_company_data(company_name, chart_template=chart_template, **kwargs)
        res['company'].write({
            'currency_id': eur.id,
            'invoice_is_ubl_cii': True,
        })
        return res

    # =========================
    # HELPER METHODS
    # =========================
    def _assert_invoice_attachment(self, attachment, xpaths, expected_file_path):
        """Get attachment from a posted account.move, and asserts it's the same as the expected xml file."""
        self.assertTrue(attachment)

        xml_content = base64.b64decode(attachment.with_context(bin_size=False).datas)
        expected_file_path = expected_file_path.replace('.xml', '')
        if '/' not in expected_file_path:
            expected_file_path = '/' + expected_file_path
        subfolder, test_name = expected_file_path.rsplit('/', maxsplit=1)

        self.assert_xml(
            xml_element=xml_content,
            test_name=test_name,
            subfolder=subfolder,
            xpath_to_apply=xpaths,
        )

        return attachment

    @freeze_time('2026-01-01')
    def _assert_imported_invoice_from_etree(self, invoice, attachment):
        """
        Create an account.move directly from an xml file,
        asserts the invoice obtained is the same as the expected invoice.
        """
        # /!\ use the same journal as the invoice's one to import the attachment !
        invoice.journal_id.create_document_from_attachment(attachment.ids)
        new_invoice = self.env['account.move'].search([], order='id desc', limit=1)

        self.assertTrue(new_invoice)
        self.assert_same_invoice(invoice, new_invoice)

    def assert_same_invoice(self, invoice1, invoice2):
        self.assertEqual(len(invoice1.invoice_line_ids), len(invoice2.invoice_line_ids))
        self.assertRecordValues(invoice2, [{
            'partner_id': invoice1.partner_id.id,
            'invoice_date': fields.Date.from_string(invoice1.date),
            'currency_id': invoice1.currency_id.id,
            'amount_untaxed': invoice1.amount_untaxed,
            'amount_tax': invoice1.amount_tax,
            'amount_total': invoice1.amount_total,
        }])

        self.assertRecordValues(invoice2.invoice_line_ids, [{
            'quantity': line.quantity,
            'price_unit': line.price_unit,
            'discount': line.discount,
            'product_id': line.product_id.id,
            'product_uom_id': line.product_uom_id.id,
            'tax_ids': line.tax_ids.ids,
        } for line in invoice1.invoice_line_ids])

    @freeze_time('2026-01-01')
    def _generate_move(self, seller, buyer, send=True, **invoice_kwargs):
        """Create and post an account.move."""

        # Setup the seller.
        self.env.company.write({
            'partner_id': seller.id,
            'name': seller.name,
            'street': seller.street,
            'zip': seller.zip,
            'city': seller.city,
            'vat': seller.vat,
            'country_id': seller.country_id.id,
        })

        move_type = invoice_kwargs['move_type']
        account_move = self.env['account.move'].create({
            'partner_id': buyer.id,
            'partner_bank_id': (seller if move_type == 'out_invoice' else buyer).bank_ids[:1].id,
            'invoice_date': '2026-01-01',
            'invoice_date_due': '2026-01-01',
            'date': '2026-01-01',
            'currency_id': self.env.ref('base.EUR').id,
            **invoice_kwargs,
            'invoice_line_ids': [
                (0, 0, {
                    'sequence': i,
                    **invoice_line_kwargs,
                })
                for i, invoice_line_kwargs in enumerate(invoice_kwargs.get('invoice_line_ids', []))
            ],
        })

        account_move.action_post()
        if send:
            account_move._generate_pdf_and_send_invoice(self.move_template)
        return account_move
