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

    def _compute_edi_error_count(self):
        super()._compute_edi_error_count()
        for move in self:
            if (
                move.country_code == "IN"
                and any(move.edi_document_ids.filtered(
                    lambda d: d.edi_format_id.code in ["in_einvoice_1_03", "in_ewaybill_1_03"] and d.state in ("to_send", "sent") and not d.blocking_level
                ))
                and self.env["ir.config_parameter"].sudo().get_param("l10n_in.gsp_provider", "tera") == "tera"
            ):
                move.edi_error_count = 1

    def _compute_edi_error_message(self):
        super()._compute_edi_error_message()
        for move in self:
            if (
                move.country_code == "IN"
                and any(move.edi_document_ids.filtered(
                    lambda d: d.edi_format_id.code in ["in_einvoice_1_03", "in_ewaybill_1_03"] and d.state in ("to_send", "sent") and not d.blocking_level
                ))
                and self.env["ir.config_parameter"].sudo().get_param("l10n_in.gsp_provider", "tera") == "tera"
            ):
                edi_error_message = _(
                    "<b><span class='fa fa-warning'/> Important Notice – GSP Deprecation <br></b>"
                    "The currently selected GSP (Tera Soft) will be deprecated soon.<br>"
                    "To ensure uninterrupted e-Invoice and E-way operations, <b>please switch to BVM GSP as per the </b>"
                    "<a href='https://www.odoo.com/documentation/18.0/applications/finance/fiscal_localizations/india.html#gsp-configuration'>documentation</a>."
                )
                if not self.env.is_admin():
                    edi_error_message += _(
                        "<br><br><i>You must contact your system administrator to update the GSP.</i>"
                    )
                move.edi_error_message = edi_error_message
                move.edi_blocking_level = 'warning'

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
