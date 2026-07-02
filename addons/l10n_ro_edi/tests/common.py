from unittest.mock import patch

from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged("post_install_l10n", "post_install", "-at_install")
class TestROEdiCommon(AccountTestInvoicingCommon):
    _test_groups = None  # FIXME list needed groups

    @classmethod
    @AccountTestInvoicingCommon.setup_country("ro")
    def setUpClass(cls):
        super().setUpClass()

        cls.company_data["company"].write(
            {
                "state_id": cls.env.ref("base.RO_B").id,
                "city": "SECTOR1",
                "zip": "010101",
                "vat": "RO1234567897",
                "phone": "+40 123 456 789",
                "street": "Strada Test, 3",
                "l10n_ro_edi_access_token": "test_token",
            }
        )

        cls.partner_ro = cls.env["res.partner"].create(
            {
                "name": "Romanian Test Partner",
                "country_id": cls.env.ref("base.ro").id,
                "state_id": cls.env.ref("base.RO_B").id,
                "city": "SECTOR3",
                "zip": "010101",
                "vat": "RO1234567897",
                "phone": "+40 123 456 780",
                "street": "Strada Partner, 88",
                "invoice_edi_format": "ciusro",
            }
        )

        cls.tax_19 = cls.env["account.tax"].create(
            {
                "name": "tax_19",
                "amount_type": "percent",
                "amount": 19,
                "type_tax_use": "sale",
                "country_id": cls.env.ref("base.ro").id,
            }
        )

    def create_invoice(self, move_type="out_invoice", **kwargs):
        """Create and post a Romanian invoice ready for EDI sending."""
        vals = {
            "move_type": move_type,
            "partner_id": self.partner_ro.id,
            "invoice_line_ids": [
                Command.create(
                    {
                        "name": "Test Product",
                        "quantity": 1,
                        "price_unit": 500.0,
                        "tax_ids": [Command.set(self.tax_19.ids)],
                    }
                ),
            ],
        }
        vals.update(kwargs)
        invoice = self.env["account.move"].create(vals)
        invoice.action_post()
        return invoice

    def send_invoice_with_mock(self, invoice, mock_return_value):
        """Helper to send invoice mocking the SPV response."""
        with patch(
            'odoo.addons.l10n_ro_edi.models.account_move._request_ciusro_send_invoice',
            return_value=mock_return_value,
        ):
            invoice._l10n_ro_edi_send_invoice(
                xml_data=invoice.ubl_cii_xml_id.raw if invoice.ubl_cii_xml_id else b"<xml>test</xml>",
            )

    def synchronize_with_mock(self, mock_return_value):
        """Helper to run synchronize mocking the SPV response."""
        with patch(
            'odoo.addons.l10n_ro_edi.models.account_move._request_ciusro_synchronize_invoices',
            return_value=mock_return_value,
        ):
            self.env["account.move"]._l10n_ro_edi_fetch_invoices()
