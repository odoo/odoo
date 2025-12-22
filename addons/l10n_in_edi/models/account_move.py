# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from markupsafe import Markup

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_in_edi_cancel_reason = fields.Selection(selection=[
        ("1", "Duplicate"),
        ("2", "Data Entry Mistake"),
        ("3", "Order Cancelled"),
        ("4", "Others"),
        ], string="Cancel reason", copy=False)
    l10n_in_edi_cancel_remarks = fields.Char("Cancel remarks", copy=False)
    l10n_in_edi_show_cancel = fields.Boolean(compute="_compute_l10n_in_edi_show_cancel", string="E-invoice(IN) is sent?")

    @api.depends('edi_document_ids')
    def _compute_l10n_in_edi_show_cancel(self):
        for invoice in self:
            invoice.l10n_in_edi_show_cancel = bool(invoice.edi_document_ids.filtered(
                lambda i: i.edi_format_id.code == "in_einvoice_1_03"
                and i.state in ("sent", "to_cancel", "cancelled")
            ))

    def action_retry_edi_documents_error(self):
        for move in self:
            if move.country_code == 'IN':
                move.message_post(body=_(
                    "Retrying EDI processing for the following documents: %(breakline)s %(edi_codes)s",
                    breakline=Markup("<br/>"),
                    edi_codes=Markup("<br/>").join(
                        move.edi_document_ids
                        .filtered(lambda doc: doc.blocking_level == "error")
                        .mapped("edi_format_name")
                    )
                ))
        return super().action_retry_edi_documents_error()

    def button_cancel_posted_moves(self):
        """Mark the edi.document related to this move to be canceled."""
        reason_and_remarks_not_set = self.env["account.move"]
        for move in self:
            send_l10n_in_edi = move.edi_document_ids.filtered(lambda doc: doc.edi_format_id.code == "in_einvoice_1_03")
            # check submitted E-invoice does not have reason and remarks
            # because it's needed to cancel E-invoice
            if send_l10n_in_edi and (not move.l10n_in_edi_cancel_reason or not move.l10n_in_edi_cancel_remarks):
                reason_and_remarks_not_set += move
        if reason_and_remarks_not_set:
            raise UserError(_(
                "To cancel E-invoice set cancel reason and remarks at Other info tab in invoices: \n%s",
                ("\n".join(reason_and_remarks_not_set.mapped("name"))),
            ))
        return super().button_cancel_posted_moves()

    def _get_l10n_in_edi_response_json(self):
        self.ensure_one()
        l10n_in_edi = self.edi_document_ids.filtered(lambda i: i.edi_format_id.code == "in_einvoice_1_03"
            and i.state in ("sent", "to_cancel"))
        if l10n_in_edi:
            return json.loads(l10n_in_edi.sudo().attachment_id.raw.decode("utf-8"))
        else:
            return {}

    def _can_force_cancel(self):
        # OVERRIDE
        self.ensure_one()
        return any(document.edi_format_id.code == 'in_einvoice_1_03' and document.state == 'to_cancel' for document in self.edi_document_ids) or super()._can_force_cancel()
