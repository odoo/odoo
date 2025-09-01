# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields
from odoo.addons.l10n_tw_edi_ecpay.utils import call_ecpay_api
from odoo.exceptions import UserError


class L10nTwEDIInvoicePrint(models.TransientModel):
    _name = "l10n_tw_edi.invoice.print"
    _description = "Implements printingan ecpay invoice."

    invoice_id = fields.Many2one(
        comodel_name="account.move",
        string="Document To Print",
        required=True,
        readonly=True,
    )
    print_format_b2c = fields.Selection(
        string="Print Format (B2C)",
        selection=[
            ("1", "single-sided printing"),
            ("2", "double-sided printing"),
            ("3", "printing with thermal paper"),
        ],
        default="1",
    )
    print_format_b2b = fields.Selection(
        string="Print Format (B2B)",
        selection=[
            ("1", "A4 printing "),
            ("2", "A5 printing "),
        ],
        default="1",
    )
    l10n_tw_edi_is_b2b = fields.Boolean(string="Is B2B", related="invoice_id.l10n_tw_edi_is_b2b")

    def button_print(self):
        self.ensure_one()

        json_data = {
            "MerchantID": self.invoice_id.company_id.sudo().l10n_tw_edi_ecpay_merchant_id,
            "InvoiceNo": self.invoice_id.l10n_tw_edi_ecpay_invoice_id,
            "InvoiceDate": self.invoice_id.l10n_tw_edi_invoice_create_date.strftime("%Y-%m-%d"),
            "PrintStyle": self.print_format_b2b if self.l10n_tw_edi_is_b2b else self.print_format_b2c,
            "IsShowingDetail": "1",
        }

        response_data = call_ecpay_api("/InvoicePrint", json_data, self.invoice_id.company_id, self.l10n_tw_edi_is_b2b)
        if response_data.get('RtnCode') != 1:
            raise UserError(self.env._("Error: %(error)s", error=response_data.get('RtnMsg')))

        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': response_data.get("InvoiceHtml"),
        }
