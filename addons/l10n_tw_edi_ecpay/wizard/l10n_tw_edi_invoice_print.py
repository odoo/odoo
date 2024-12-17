from odoo import models, fields
from odoo.addons.l10n_tw_edi_ecpay.utils import EcPayAPI
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

    print_format = fields.Selection(
        string="Print Format",
        selection=[
            ("1", "single-sided printing"),
            ("2", "double-sided printing"),
            ("3", "printing with thermal paper"),
            ("4", "B2B A4 (Only invoices with Tax ID Number can be used)"),
            ("5", "B2B A5 (Only invoices with Tax ID Number can be used)"),
        ],
        default="1",
        required=True,
    )

    def button_print(self):
        self.ensure_one()
        ecpay_api = EcPayAPI(self.invoice_id.company_id)

        json_data = {
            "MerchantID": self.invoice_id.company_id.sudo().l10n_tw_edi_ecpay_merchant_id,
            "InvoiceNo": self.invoice_id.l10n_tw_edi_ecpay_invoice_id,
            "InvoiceDate": self.invoice_id.l10n_tw_edi_invoice_create_date.strftime("%Y-%m-%d"),
            "PrintStyle": self.print_format,
            "IsShowingDetail": "1",
        }

        response_data = ecpay_api.call_ecpay_api("/InvoicePrint", json_data)
        if response_data.get('RtnCode') != 1:
            raise UserError(self.env._("Error: %(error)s", error=response_data.get('RtnMsg')))

        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': response_data.get("InvoiceHtml"),
        }
