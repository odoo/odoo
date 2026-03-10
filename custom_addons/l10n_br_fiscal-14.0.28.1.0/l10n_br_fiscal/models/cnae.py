# Copyright (C) 2009 Renato Lima - Akretion <renato.lima@akretion.com.br>
# Copyright (C) 2014  KMEE - www.kmee.com.br
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import _, fields, models


class Cnae(models.Model):
    _name = "l10n_br_fiscal.cnae"
    _inherit = "l10n_br_fiscal.data.abstract"
    _description = "CNAE"

    code = fields.Char(size=16)

    version = fields.Char(size=16, required=True)

    parent_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.cnae", string="Parent CNAE"
    )

    child_ids = fields.One2many(
        comodel_name="l10n_br_fiscal.cnae",
        inverse_name="parent_id",
        string="Children CNAEs",
    )

    internal_type = fields.Selection(
        selection=[("view", "View"), ("normal", "Normal")],
        required=True,
        default="normal",
    )

    _sql_constraints = [
        (
            "fiscal_cnae_code_uniq",
            "unique (code)",
            _("CNAE already exists with this code !"),
        )
    ]
