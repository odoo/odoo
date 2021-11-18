# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    edi_state = fields.Selection(
        selection_add=[("to_confrim", "To Confrim")], compute="_compute_edi_state"
    )
    edi_web_services_to_confrim = fields.Text(
        compute="_compute_edi_web_services_to_confrim",
        help="Technical field to display the documents that will be to confrim",
    )

    @api.depends("edi_document_ids.state")
    def _compute_edi_state(self):
        super()._compute_edi_state()
        for move in self:
            if move.edi_document_ids.filtered(
                lambda d: d.edi_format_id._needs_web_services()
                and d.state == "to_confrim"
            ):
                move.edi_state = "to_confrim"

    @api.depends(
        "edi_document_ids",
        "edi_document_ids.state",
        "edi_document_ids.blocking_level",
        "edi_document_ids.edi_format_id",
    )
    def _compute_edi_web_services_to_confrim(self):
        for move in self:
            to_process_manually = move.edi_document_ids.filtered(
                lambda d: d.state == "to_confrim"
            )
            format_web_services = to_process_manually.edi_format_id.filtered(
                lambda f: f._needs_web_services()
            )
            move.edi_web_services_to_confrim = ", ".join(
                f.name for f in format_web_services
            )

    def _post(self, soft=True):
        posted = super()._post(soft=soft)
        edi_document_set_to_confrim = self.env["account.edi.document"]
        for move in posted:
            for edi_format in move.journal_id.edi_format_ids:
                if edi_format.double_check_on_web_service:
                    edi_document_set_to_confrim += move.edi_document_ids.filtered(
                        lambda x: x.edi_format_id == edi_format and x.state == "to_send"
                    )
        edi_document_set_to_confrim.write({"state": "to_confrim"})
        return posted

    def action_process_edi_web_services_confrim(self):
        docs = self.edi_document_ids.filtered(
            lambda d: d.state == "to_confrim" and d.blocking_level != "error"
        )
        docs.write({"state": "to_send"})
        self.env.ref("account_edi.ir_cron_edi_network")._trigger()
