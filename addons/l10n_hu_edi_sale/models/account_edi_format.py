# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class AccountEdiFormat(models.Model):
    _inherit = "account.edi.format"

    @api.model
    def _l10n_hu_edi_generate_xml_line_data(self, invoice):
        data = super()._l10n_hu_edi_generate_xml_line_data(invoice)
        for line_data in data:
            line = line_data["line_object"]
            if line.display_type == "product":
                # Mark Advance and Final Invoices
                if line.move_id._l10n_hu_get_special_invoice_type() == "advance":
                    line_data.update({"is_advance": True})

                elif line.move_id._l10n_hu_get_special_invoice_type() == "final":
                    advanced_invoice = None

                    # only one invoice can be sent, so if there is more than one, none will be sent
                    # (that is xml standard comfort)
                    advanced_invoice_obj = (
                        line._get_downpayment_lines().mapped("move_id").filtered(lambda i: i.state == "posted")
                    )
                    if len(advanced_invoice_obj) == 1:
                        advanced_invoice = advanced_invoice_obj

                    line_data.update(
                        {
                            "is_advance": True,
                            "advanced_invoice": advanced_invoice,
                        }
                    )

        return data
