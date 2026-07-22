from odoo import fields, models
from odoo.exceptions import UserError

from odoo.addons.l10n_ge_edi.tools.rsge_client import RSgeError, translate_rsge_error


class L10nGeEdiKInvoiceWizard(models.TransientModel):
    _name = "l10n_ge_edi.k_invoice.wizard"
    _description = "RS.ge Corrective Invoice Type"

    move_id = fields.Many2one(comodel_name="account.move", required=True, readonly=True)

    def _l10n_ge_edi_create_k_invoice_credit_note(self, k_type):
        self.ensure_one()
        original = self.move_id
        if original.l10n_ge_edi_k_invoice_not_allowed:
            raise UserError(self.env._("This invoice must be confirmed by RS.ge before a corrective invoice can be created."))

        company = original.company_id
        client = company._l10n_ge_edi_get_client()
        user_id = company.sudo().l10n_ge_edi_user_id

        try:
            k_id = client.save_k_invoice(user_id=user_id, invoice_id=original._l10n_ge_edi_get_invoice_id(), k_type=int(k_type))
        except RSgeError as error:
            raise UserError(translate_rsge_error(self.env, error)) from error

        new_move = original._reverse_moves([{"l10n_ge_edi_invoice_id": str(k_id), "l10n_ge_edi_k_type": k_type}])
        new_move.l10n_ge_edi_original_move_id = original.id
        original.l10n_ge_edi_correction_move_id = new_move.id

        original.message_post(body=self.env._("Corrective invoice created: %(new_move)s", new_move=new_move._get_html_link()))

        return new_move

    def _l10n_ge_edi_create_k_invoice_type_1(self):
        self.ensure_one()
        new_move = self._l10n_ge_edi_create_k_invoice_credit_note("1")

        new_move.action_post()
        new_move._l10n_ge_edi_submit_k_invoice_type_1()

        self.move_id.action_l10n_ge_edi_refresh_status()

        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "form",
            "res_id": new_move.id,
        }

    def _l10n_ge_edi_create_k_invoice_type_4(self):
        self.ensure_one()
        new_move = self._l10n_ge_edi_create_k_invoice_credit_note("4")

        self.move_id.action_l10n_ge_edi_refresh_status()

        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "form",
            "res_id": new_move.id,
        }

    def _l10n_ge_edi_create_k_invoice_type_3(self):
        self.ensure_one()
        original = self.move_id
        if original.l10n_ge_edi_k_invoice_not_allowed:
            raise UserError(self.env._("This invoice must be confirmed by RS.ge before a corrective invoice can be created."))
        if original._l10n_ge_edi_has_reconciled_payment():
            raise UserError(
                self.env._(
                    "This invoice has reconciled payments and cannot be modified, since that "
                    "would cancel it and incorrectly unreconcile the payment. Use Cancel "
                    "Transaction instead, then create a new invoice.",
                ),
            )

        company = original.company_id
        client = company._l10n_ge_edi_get_client()
        user_id = company.sudo().l10n_ge_edi_user_id

        try:
            k_id = client.save_k_invoice(user_id=user_id, invoice_id=original._l10n_ge_edi_get_invoice_id(), k_type=3)
            remote_lines = client.get_invoice_lines(user_id=user_id, invoice_id=k_id)
        except RSgeError as error:
            raise UserError(translate_rsge_error(self.env, error)) from error

        new_move = original.copy({"l10n_ge_edi_invoice_id": str(k_id), "l10n_ge_edi_k_type": "3"})

        new_lines = new_move.invoice_line_ids.filtered(lambda line: line.display_type == "product")
        for line, remote_line in zip(new_lines, remote_lines):
            line.l10n_ge_edi_line_id = remote_line["ID"]

        new_move.l10n_ge_edi_original_move_id = original.id
        original.l10n_ge_edi_correction_move_id = new_move.id

        original.message_post(body=self.env._("Corrective invoice created: %(new_move)s", new_move=new_move._get_html_link()))

        original.action_l10n_ge_edi_refresh_status()
        original.button_cancel()

        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "form",
            "res_id": new_move.id,
        }

    def action_taxable_transaction_cancelled(self):
        self.ensure_one()
        return self._l10n_ge_edi_create_k_invoice_type_1()

    def action_modify_invoice(self):
        self.ensure_one()
        return self._l10n_ge_edi_create_k_invoice_type_3()

    def action_full_partial_refund(self):
        self.ensure_one()
        return self._l10n_ge_edi_create_k_invoice_type_4()
