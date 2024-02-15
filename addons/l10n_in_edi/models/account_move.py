# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import api, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

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

    @api.model
    def _l10n_in_edi_is_managing_invoice_negative_lines_allowed(self):
        """ Negative lines are not allowed by the Indian government making some features unavailable like sale_coupon
        or global discounts. This method allows odoo to distribute the negative discount lines to each others lines
        with same HSN code making such features available even for Indian people.
        :return: True if odoo needs to distribute the negative discount lines, False otherwise.
        """
        param_name = 'l10n_in_edi.manage_invoice_negative_lines'
        return bool(self.env['ir.config_parameter'].sudo().get_param(param_name))
