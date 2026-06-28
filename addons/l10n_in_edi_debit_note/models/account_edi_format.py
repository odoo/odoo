# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class DebitNote(models.Model):
    _inherit = "account.edi.format"

    def _l10n_in_edi_generate_invoice_json(self, invoice):
        json_payload = super(DebitNote, self)._l10n_in_edi_generate_invoice_json(invoice)
        if invoice.debit_origin_id:
            json_payload["DocDtls"]["Typ"] = "DBN"
        return json_payload
