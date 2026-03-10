# Copyright (C) 2020  Renato Lima - Akretion <renato.lima@akretion.com.br>
# Copyright (C) 2020 Luis Felipe Miléo - KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class BaseWizardMixin(models.TransientModel):
    _name = "l10n_br_fiscal.base.wizard.mixin"
    _description = "Fiscal Base Wizard Mixin"

    document_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.document",
        string="Fiscal Document",
    )

    document_type_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.document.type",
        string="Document Type",
    )

    document_type = fields.Char(
        related="document_type_id.code",
    )

    document_key = fields.Char()

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Partner",
    )

    rps_number = fields.Char()

    document_number = fields.Char()

    document_serie = fields.Char()

    justification = fields.Text()

    document_status = fields.Text(string="Status", readonly=True)

    state = fields.Selection(
        selection=[("init", "init"), ("confirm", "confirm"), ("done", "done")],
        readonly=True,
        default="init",
    )

    def _prepare_key_fields(self):
        return {
            "l10n_br_fiscal.document": "document_id",
            "res.partner": "partner_id",
        }

    def _document_fields(self):
        return [
            "document_key",
            "document_number",
            "document_serie",
            "document_type_id",
            "partner_id",
            "rps_number",
        ]

    @api.model
    def default_get(self, fields_list):
        default_values = super().default_get(fields_list)
        active_model = self._context.get("active_model")

        if self._prepare_key_fields().get(active_model):
            active_id = self._context["active_id"]
            active_vals = (
                self.env[active_model]
                .browse(active_id)
                .read(self._document_fields())[0]
            )
            active_vals = self._convert_to_write(active_vals)
            active_vals.pop("id")
            default_values.update(active_vals)

            default_values.update({self._prepare_key_fields()[active_model]: active_id})
        return default_values

    def button_back(self):
        self.ensure_one()
        self.state = "init"
        return self._reopen()

    def _reopen(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "view_mode": "form",
            "view_type": "form",
            "res_id": self.id,
            "views": [(False, "form")],
            "target": "new",
            "nodestroy": True,
        }

    def _close(self):
        return {"type": "ir.actions.act_window_close"}
