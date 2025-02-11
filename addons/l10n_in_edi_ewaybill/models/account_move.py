# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    # Transaction Details
    l10n_in_type_id = fields.Many2one("l10n.in.ewaybill.type", "E-waybill Document Type", tracking=True)

    # transportation details
    l10n_in_distance = fields.Integer("Distance", tracking=True)
    l10n_in_mode = fields.Selection([
        ("0", "Managed by Transporter"),
        ("1", "Road"),
        ("2", "Rail"),
        ("3", "Air"),
        ("4", "Ship")],
        string="Transportation Mode", copy=False, tracking=True)

    # Vehicle Number and Type required when transportation mode is By Road.
    l10n_in_vehicle_no = fields.Char("Vehicle Number", copy=False, tracking=True)
    l10n_in_vehicle_type = fields.Selection([
        ("R", "Regular"),
        ("O", "Over Dimensional Cargo")],
        string="Vehicle Type", copy=False, tracking=True)

    # Document number and date required in case of transportation mode is Rail, Air or Ship.
    l10n_in_transportation_doc_no = fields.Char(
        string="E-waybill Document Number",
        help="""Transport document number. If it is more than 15 chars, last 15 chars may be entered""",
        copy=False, tracking=True)
    l10n_in_transportation_doc_date = fields.Date(
        string="Document Date",
        help="Date on the transporter document",
        copy=False,
        tracking=True)

    # transporter id required when transportation done by other party.
    l10n_in_transporter_id = fields.Many2one("res.partner", "Transporter", copy=False, tracking=True)
    # show and hide fields base on this
    l10n_in_edi_ewaybill_direct_api = fields.Boolean(string="E-waybill(IN) direct API", compute="_compute_l10n_in_edi_ewaybill_direct")
    l10n_in_edi_ewaybill_show_send_button = fields.Boolean(string="Show Send E-waybill Button", compute="_compute_l10n_in_edi_ewaybill_show_send_button")

    @api.depends('state', 'edi_document_ids', 'edi_document_ids.state')
    def _compute_l10n_in_edi_ewaybill_show_send_button(self):
        edi_format = self.env.ref('l10n_in_edi_ewaybill.edi_in_ewaybill_json_1_03', raise_if_not_found=False)
        if not edi_format:
            self.l10n_in_edi_ewaybill_show_send_button = False
            return
        posted_moves = self.filtered(lambda x: x.is_invoice() and x.state == 'posted' and x.country_code == "IN")
        for move in posted_moves:
            already_sent = move.edi_document_ids.filtered(lambda x: x.edi_format_id == edi_format and x.state in ('sent', 'to_cancel', 'to_send'))
            if already_sent:
                move.l10n_in_edi_ewaybill_show_send_button = False
            else:
                move.l10n_in_edi_ewaybill_show_send_button = True
        (self - posted_moves).l10n_in_edi_ewaybill_show_send_button = False

    @api.depends("l10n_in_gst_treatment")
    def _compute_l10n_in_edi_ewaybill_direct(self):
        for move in self:
            base = self.env["account.edi.format"]._l10n_in_edi_ewaybill_base_irn_or_direct(move)
            move.l10n_in_edi_ewaybill_direct_api = base == "direct"

    @api.depends("edi_document_ids")
    def _compute_l10n_in_edi_show_cancel(self):
        super()._compute_l10n_in_edi_show_cancel()
        for invoice in self:
            if invoice.edi_document_ids.filtered(lambda i: i.edi_format_id.code == "in_ewaybill_1_03" and i.state in ("sent", "to_cancel", "cancelled")):
                invoice.l10n_in_edi_show_cancel = True

    def _get_l10n_in_edi_ewaybill_response_json(self):
        self.ensure_one()
        l10n_in_edi = self.edi_document_ids.filtered(lambda i: i.edi_format_id.code == "in_ewaybill_1_03"
            and i.state in ("sent", "to_cancel"))
        if l10n_in_edi and l10n_in_edi.sudo().attachment_id:
            return json.loads(l10n_in_edi.sudo().attachment_id.raw.decode("utf-8"))
        else:
            return {}

    def button_cancel_posted_moves(self):
        """Mark the edi.document related to this move to be canceled."""
        reason_and_remarks_not_set = self.env["account.move"]
        for move in self:
            send_l10n_in_edi_ewaybill = move.edi_document_ids.filtered(lambda doc: doc.edi_format_id.code == "in_ewaybill_1_03")
            # check submitted E-waybill does not have reason and remarks
            # because it's needed to cancel E-waybill
            if send_l10n_in_edi_ewaybill and (not move.l10n_in_edi_cancel_reason or not move.l10n_in_edi_cancel_remarks):
                reason_and_remarks_not_set += move
        if reason_and_remarks_not_set:
            raise UserError(_(
                "To cancel E-waybill set cancel reason and remarks at E-waybill tab in: \n%s",
                ("\n".join(reason_and_remarks_not_set.mapped("name"))),
            ))
        return super().button_cancel_posted_moves()

    def l10n_in_edi_ewaybill_send(self):
        edi_format = self.env.ref('l10n_in_edi_ewaybill.edi_in_ewaybill_json_1_03')
        edi_document_vals_list = []
        for move in self:
            if move.state != 'posted':
                raise UserError(_("You can only create E-waybill from posted invoice"))
            errors = edi_format._check_move_configuration(move)
            if errors:
                raise UserError(_("Invalid invoice configuration:\n\n%s", '\n'.join(errors)))
            existing_edi_document = move.edi_document_ids.filtered(lambda x: x.edi_format_id == edi_format)
            if existing_edi_document:
                if existing_edi_document.state in ('sent', 'to_cancel'):
                    raise UserError(_("E-waybill is already created"))
                existing_edi_document.sudo().write({
                    'state': 'to_send',
                    'attachment_id': False,
                })
            else:
                edi_document_vals_list.append({
                    'edi_format_id': edi_format.id,
                    'move_id': move.id,
                    'state': 'to_send',
                })
        self.env['account.edi.document'].create(edi_document_vals_list)
        self.env.ref('account_edi.ir_cron_edi_network')._trigger()

    def _can_force_cancel(self):
        # OVERRIDE
        self.ensure_one()
        return any(document.edi_format_id.code == 'in_ewaybill_1_03' and document.state == 'to_cancel' for document in self.edi_document_ids) or super()._can_force_cancel()
