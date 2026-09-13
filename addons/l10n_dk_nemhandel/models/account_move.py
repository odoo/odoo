from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.account.tools.import_file_type import CUSTOMIZATION_ID, findtext_equals


class AccountMove(models.Model):
    _inherit = "account.move"

    nemhandel_message_uuid = fields.Char(
        string="Nemhandel message ID",
        copy=False,
    )
    nemhandel_move_state = fields.Selection(
        selection=[
            ("ready", "Ready to send"),
            ("to_send", "Queued"),
            ("processing", "Pending Reception"),
            ("done", "Done"),
            ("error", "Error"),
        ],
        string="Nemhandel status",
        compute="_compute_nemhandel_move_state",
        store=True,
        copy=False,
    )

    @api.depends("state")
    def _compute_nemhandel_move_state(self):
        for move in self:
            if all(
                [
                    move.company_id.l10n_dk_nemhandel_proxy_state == "receiver",
                    move.commercial_partner_id.nemhandel_verification_state == "valid",
                    move.state == "posted",
                    move.is_sale_document(include_receipts=True),
                    not move.nemhandel_move_state,
                ]
            ):
                move.nemhandel_move_state = "ready"
            elif (
                move.state == "draft"
                and move.is_sale_document(include_receipts=True)
                and move.nemhandel_move_state not in {"processing", "done"}
            ):
                move.nemhandel_move_state = False
            else:
                move.nemhandel_move_state = move.nemhandel_move_state

    def _import_file_type_rules(self):
        # EXTENDS 'account'
        return [
            (
                "account.edi.xml.oioubl_21",
                findtext_equals(CUSTOMIZATION_ID, "OIOUBL-2.1"),
            ),
            *super()._import_file_type_rules(),
        ]

    def action_cancel_nemhandel_documents(self):
        # if the nemhandel_move_state is processing/done
        # then it means it has been already sent to nemhandel proxy and we can't cancel
        if any(move.nemhandel_move_state in {"processing", "done"} for move in self):
            raise UserError(
                _("Cannot cancel an entry that has already been sent to Nemhandel")
            )
        self.nemhandel_move_state = False
        self.sending_data = False

    def action_send_and_print(self):
        for move in self:
            move.commercial_partner_id.button_nemhandel_check_partner_endpoint(
                company=move.company_id
            )
        return super().action_send_and_print()

    def _is_ubl_cii_xml_required(self, ubl_cii_format):
        if ubl_cii_format == "oioubl_21" and (
            not self.partner_id.vat
            or self.partner_id._get_nemhandel_verification_state(ubl_cii_format)
            != "valid"
        ):
            return False
        return super()._is_ubl_cii_xml_required(ubl_cii_format)
