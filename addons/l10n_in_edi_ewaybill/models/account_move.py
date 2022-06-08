# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    # Transaction Details
    l10n_in_transaction_type = fields.Selection(
        [
            ("1", "Regular"),
            ("2", "Bill To-Ship To"),
            ("3", "Bill From-Dispatch From"),
            ("4", "Combination of 2 and 3"),
        ],
        string="Transaction Type",
        copy=False
    )
    l10n_in_type_id = fields.Many2one("l10n.in.ewaybill.type", "Document Type")
    l10n_in_subtype_id = fields.Many2one("l10n.in.ewaybill.type", "Sub Supply Type")

    @api.onchange('l10n_in_type_id')
    def _onchange_l10n_in_type_id(self):
        self.l10n_in_subtype_id = False

    @api.depends('edi_document_ids')
    def _compute_l10n_in_edi_show_cancel(self):
        super()._compute_l10n_in_edi_show_cancel()
        for invoice in self:
            invoice.l10n_in_edi_show_cancel = bool(invoice.edi_document_ids.filtered(
                lambda i: i.edi_format_id.code == "edi_in_ewaybill_json_1_03"
                and i.state in ("sent", "to_cancel", "cancelled")
            ))

    def button_cancel_posted_moves(self):
        """Mark the edi.document related to this move to be canceled."""
        reason_and_remarks_not_set = self.env["account.move"]
        for move in self:
            send_l10n_in_edi = move.edi_document_ids.filtered(lambda doc: doc.edi_format_id.code == "edi_in_ewaybill_json_1_03")
            # check submitted E-Waybill does not have reason and remarks
            # because it's needed to cancel E-Waybill
            if send_l10n_in_edi and (not move.l10n_in_edi_cancel_reason or not move.l10n_in_edi_cancel_remarks):
                reason_and_remarks_not_set += move
        if reason_and_remarks_not_set:
            raise UserError(_(
                "To cancel E-Waybill set cancel reason and remarks at Other info tab in invoices: \n%s",
                ("\n".join(reason_and_remarks_not_set.mapped("name"))),
            ))
        return super().button_cancel_posted_moves()

    def _get_l10n_in_edi_response_json(self):
        self.ensure_one()
        l10n_in_edi = self.edi_document_ids.filtered(lambda i: i.edi_format_id.code == "edi_in_ewaybill_json_1_03"
            and i.state in ("sent", "to_cancel"))
        if l10n_in_edi:
            return json.loads(l10n_in_edi.attachment_id.raw.decode("utf-8"))
        else:
            return {}
