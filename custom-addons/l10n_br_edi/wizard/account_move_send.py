# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _


class AccountMoveSend(models.TransientModel):
    _inherit = "account.move.send"

    l10n_br_edi_is_visible = fields.Boolean(
        compute="_compute_l10n_br_edi_is_visible",
        help="Brazil: technical field to determine if the option to submit a Brazilian electronic invoice is visible.",
    )
    l10n_br_edi_is_enabled = fields.Boolean(
        compute="_compute_l10n_br_edi_is_enabled",
        string="Process e-invoice",
        store=True,
        readonly=False,
        help="Brazil: used to determine whether to submit this e-invoice.",
    )
    l10n_br_edi_warning = fields.Text(
        "Warning",
        compute="_compute_l10n_br_edi_warning",
        readonly=True,
        help="Brazil: used to display warnings in the wizard before sending.",
    )

    @api.depends("move_ids")
    def _compute_l10n_br_edi_is_visible(self):
        for wizard in self:
            wizard.l10n_br_edi_is_visible = any(move.l10n_br_edi_is_needed for move in wizard.move_ids)

    @api.depends("l10n_br_edi_is_visible")
    def _compute_l10n_br_edi_is_enabled(self):
        for wizard in self:
            # Enable e-invoicing by default if possible for this invoice.
            wizard.l10n_br_edi_is_enabled = wizard.l10n_br_edi_is_visible

    @api.depends("l10n_br_edi_is_enabled", "move_ids")
    def _compute_l10n_br_edi_warning(self):
        self.l10n_br_edi_warning = False
        for wizard in self.filtered("l10n_br_edi_is_enabled"):
            if non_eligible := wizard.move_ids.filtered(lambda move: not move.l10n_br_edi_is_needed):
                wizard.l10n_br_edi_warning = _(
                    "Brazilian e-invoicing was enabled but the following invoices cannot be e-invoiced:\n%s\n"
                    "If this is not intended, please check if an Avatax fiscal position is used on those invoices and if the invoice isn't already e-invoiced.",
                    "\n".join(f"- {move.display_name}" for move in non_eligible),
                )

    def _get_invoice_extra_attachments(self, move):
        # EXTENDS 'account'
        return super()._get_invoice_extra_attachments(move) + move.l10n_br_edi_xml_attachment_id

    def _get_wizard_values(self):
        # EXTENDS 'account'
        res = super()._get_wizard_values()
        res["l10n_br_edi_is_enabled"] = self.l10n_br_edi_is_enabled
        return res

    @api.model
    def _get_wizard_vals_restrict_to(self, only_options):
        # EXTENDS 'account'
        values = super()._get_wizard_vals_restrict_to(only_options)
        return {
            'l10n_br_edi_is_enabled': False,
            **values,
        }

    def _get_placeholder_mail_attachments_data(self, move):
        # EXTENDS 'account'
        res = super()._get_placeholder_mail_attachments_data(move)

        if self.l10n_br_edi_is_visible and self.l10n_br_edi_is_enabled:
            attachment_name = move._l10n_br_edi_get_xml_attachment_name()
            res.append(
                {
                    "id": f"placeholder_{attachment_name}",
                    "name": attachment_name,
                    "mimetype": "application/xml",
                    "placeholder": True,
                }
            )
        return res

    def _call_web_service_before_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_before_invoice_pdf_render(invoices_data)

        for invoice, invoice_data in invoices_data.items():
            # Not all invoices may need EDI.
            if not invoice_data.get("l10n_br_edi_is_enabled") or not invoice.l10n_br_edi_is_needed:
                continue

            if errors := invoice.with_company(invoice.company_id)._l10n_br_edi_send():
                invoice.l10n_br_edi_error = "\n".join(errors)
                invoice_data["error"] = {
                    "error_title": _("Errors when submitting the e-invoice:"),
                    "errors": errors,
                }
            else:
                invoice.l10n_br_edi_error = False

            if self._can_commit():
                self._cr.commit()
