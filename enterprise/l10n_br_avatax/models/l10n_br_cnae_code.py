# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api


class L10nBrCNAECode(models.Model):
    _name = "l10n_br.cnae.code"
    _description = "CNAE Code"
    _rec_names_search = ["code", "name"]

    code = fields.Char(string="Code", required=True)
    name = fields.Char(string="Name", required=True)
    sanitized_code = fields.Char(
        compute="_compute_sanitized_code",
        help="Technical field that contains the code without special characters, as expected by the Avalara API.",
    )

    @api.depends("code", "name")
    def _compute_display_name(self):
        for cnae in self:
            cnae.display_name = f"[{cnae.code}] {cnae.name}"

    @api.depends("code")
    def _compute_sanitized_code(self):
        for cnae in self:
            cnae.sanitized_code = "".join(char for char in cnae.code or "" if char.isdigit())
