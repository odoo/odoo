from odoo import Command
from odoo.tests.common import tagged
from odoo.addons.account_peppol.tests.test_peppol_messages import TestPeppolMessageCommon, FAKE_UUID


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

    def test_send_self_billed_invoice_via_peppol(self):
        """Test sending a self-billed invoice (vendor bill) via Peppol.

        Self-billed invoices are vendor bills that can be sent via Peppol when
        the company has self-billing sending activated.
        """
        self.valid_partner.ubl_cii_format = 'ubl_bis3'

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
        # In 17.0, we check enable_peppol instead of invoice_edi_format/sending_methods
        self.assertTrue(wizard.enable_peppol)

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
