from odoo import Command
from odoo.tests.common import tagged, freeze_time
from odoo.tools import file_open
from odoo.addons.account_peppol.tests.test_peppol_messages import TestPeppolMessageCommon, FAKE_UUID


@freeze_time('2023-01-01')
@tagged('-at_install', 'post_install')
class TestPeppolSelfBilling(TestPeppolMessageCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.self_billing_journal = cls.env['account.journal'].create({
            'name': 'Self Billing',
            'code': 'SB',
            'type': 'purchase',
            'is_self_billing': True,
        })

    @classmethod
    def _get_incoming_invoice_content(cls):
        with file_open('account_peppol_selfbilling/tests/assets/incoming_self_billed_invoice', mode='rb') as f:
            return f.read()

    def test_send_self_billed_invoice_via_peppol(self):
        """Test sending a self-billed invoice (vendor bill) via Peppol.

        Self-billed invoices are vendor bills that can be sent via Peppol when
        the company has self-billing sending activated.
        """
        self.valid_partner.invoice_edi_format = 'ubl_bis3'

        # Create a vendor bill (in_invoice) that can be sent as self-billed
        vendor_bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'journal_id': self.self_billing_journal.id,
            'company_id': self.env.company.id,
            'partner_id': self.valid_partner.id,
            'date': '2023-01-01',
            'invoice_date': '2023-01-01',
            'ref': 'Test vendor bill reference',
            'invoice_line_ids': [
                Command.create({
                    'name': 'vendor line 1',
                    'product_id': self.product_a.id,
                }),
                Command.create({
                    'name': 'vendor line 2',
                    'product_id': self.product_a.id,
                }),
            ],
        })
        vendor_bill.action_post()

        # Verify the bill is exportable as self-invoice
        self.assertTrue(vendor_bill._is_exportable_as_self_invoice())

        # Create and configure the send wizard
        wizard = self.create_send_and_print(vendor_bill)
        self.assertEqual(wizard.invoice_edi_format, 'ubl_bis3')
        self.assertTrue(wizard.sending_methods and 'peppol' in wizard.sending_methods)

        # Send the self-billed invoice
        wizard.action_send_and_print()

        # Verify the invoice was sent successfully
        self.env['account_edi_proxy_client.user']._cron_peppol_get_message_status()
        self.assertRecordValues(vendor_bill, [{
                'peppol_move_state': 'done',
                'peppol_message_uuid': FAKE_UUID[0],
            }],
        )
        self.assertTrue(bool(vendor_bill.ubl_cii_xml_id))

    def test_receive_self_billed_invoice_from_peppol(self):
        """Test receiving a self-billed invoice from Peppol.

        Self-billed invoices received via Peppol should be created as out_invoice
        in the self-billing reception journal.
        """
        # Set up the 21% VAT sale tax which should be put on the invoice line
        tax_21 = self.percent_tax(21.0, type_tax_use='sale')

        sale_journal = self.env['account.journal'].search([
            ('company_id', '=', self.env.company.id),
            ('type', '=', 'sale'),
        ], limit=1)

        # Receive the self-billed invoice (using existing mock data)
        # The mock data already includes a document that will be processed
        self.env['account_edi_proxy_client.user']._cron_peppol_get_new_documents()

        # Verify the self-billed invoice was created correctly
        move = self.env['account.move'].search([('peppol_message_uuid', '=', FAKE_UUID[1])])
        self.assertRecordValues(move, [{
            'peppol_move_state': 'done',
            'move_type': 'out_invoice',
            'journal_id': sale_journal.id,
        }])

        self.assertRecordValues(move.line_ids, [
            {
                'name': 'product_a',
                'quantity': 1.0,
                'price_unit': 100.0,
                'tax_ids': tax_21.ids,
                'amount_currency': -100.0,
                'currency_id': self.env.ref('base.EUR').id,
            },
            {
                'name': 'percent_21.0_(1)',
                'quantity': False,
                'price_unit': False,
                'tax_ids': [],
                'amount_currency': -21.0,
                'currency_id': self.env.ref('base.EUR').id,
            },
            {
                'name': 'BILL/2017/01/0001',
                'quantity': False,
                'price_unit': False,
                'tax_ids': [],
                'amount_currency': 121.0,
                'currency_id': self.env.ref('base.EUR').id,
            },
        ])
