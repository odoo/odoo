from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    signing_user = fields.Many2one(
        comodel_name="res.users",
        string="Signer",
        compute="_compute_signing_user",
        store=True,
        copy=False,
    )
    show_signature_area = fields.Boolean(compute="_compute_signature_area")
    signature = fields.Binary(compute="_compute_signature_area")

    @api.depends("state", "move_type", "invoice_user_id", "company_id.signing_user")
    @api.depends_context("uid")
    @_debug.perf.timed
    def _compute_signing_user(self):
        unsigned = self.filtered(
            lambda move: not move.is_sale_document() or move.state != "posted"
        )
        unsigned.signing_user = False

        is_odoobot_user = self.env.user == self.env.ref("base.user_root")
        is_backend_user = self.env.user.has_group("base.group_user")

        for invoice in self - unsigned:
            representative = invoice.company_id.signing_user
            if is_odoobot_user:
                user_can_sign = (
                    invoice.invoice_user_id
                    and invoice.invoice_user_id.has_group("base.group_user")
                )
                invoice.signing_user = representative or (
                    invoice.invoice_user_id if user_can_sign else False
                )
            else:
                invoice.signing_user = (
                    representative or self.env.user if is_backend_user else False
                )

    @api.depends(
        "state", "signing_user", "company_id.sign_invoice", "invoice_pdf_report_id"
    )
    @api.depends_context("uid")
    @_debug.perf.timed
    def _compute_signature_area(self):
        is_portal_user = self.env.user.has_group("base.group_portal")
        moves_not_to_sign = self.filtered(
            lambda inv: (
                not inv.company_id.sign_invoice
                or inv.state in {"draft", "cancel"}
                or not inv.is_sale_document()
                or (is_portal_user and not inv.invoice_pdf_report_id)
            )
        )
        moves_not_to_sign.show_signature_area = False
        moves_not_to_sign.signature = None

        invoice_with_signature = self - moves_not_to_sign
        invoice_with_signature.show_signature_area = True
        for invoice in invoice_with_signature:
            invoice.signature = invoice.signing_user.sudo().sign_signature
