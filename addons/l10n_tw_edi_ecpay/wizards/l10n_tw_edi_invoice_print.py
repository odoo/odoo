from odoo import fields, models
from odoo.exceptions import UserError

from odoo.addons.l10n_tw_edi_ecpay.utils import call_ecpay_api


class L10nTwEDIInvoicePrint(models.TransientModel):
    _name = "l10n_tw_edi.invoice.print"
    _description = "Implements printingan ecpay invoice."

    invoice_id = fields.Many2one(
        comodel_name="account.move",
        string="Document To Print",
        readonly=True,
        required=True,
    )
    print_format_b2c = fields.Selection(
        selection=[
            ("1", "single-sided printing"),
            ("2", "double-sided printing"),
            ("3", "printing with thermal paper"),
        ],
        string="Print Format (B2C)",
        default="1",
    )
    print_format_b2b = fields.Selection(
        selection=[
            ("1", "A4 printing "),
            ("2", "A5 printing "),
        ],
        string="Print Format (B2B)",
        default="1",
    )
    l10n_tw_edi_is_b2b = fields.Boolean(
        related="invoice_id.l10n_tw_edi_is_b2b",
        string="Is B2B",
    )

    def button_print(self):
        self.check_singleton()

        json_data = {
            "MerchantID": self.invoice_id.company_id.sudo().l10n_tw_edi_ecpay_merchant_id,
            "InvoiceNo": self.invoice_id.l10n_tw_edi_ecpay_invoice_id,
            "InvoiceDate": self.invoice_id.l10n_tw_edi_invoice_create_date.strftime(
                "%Y-%m-%d"
            ),
            "PrintStyle": self.print_format_b2b
            if self.l10n_tw_edi_is_b2b
            else self.print_format_b2c,
            "IsShowingDetail": "1",
        }

        response_data = call_ecpay_api(
            "/InvoicePrint",
            json_data,
            self.invoice_id.company_id,
            self.l10n_tw_edi_is_b2b,
        )
        if response_data.get("RtnCode") != 1:
            raise UserError(
                self.env._("Error: %(error)s", error=response_data.get("RtnMsg"))
            )

        return {
            "type": "ir.actions.act_url",
            "target": "new",
            "url": response_data.get("InvoiceHtml"),
        }
