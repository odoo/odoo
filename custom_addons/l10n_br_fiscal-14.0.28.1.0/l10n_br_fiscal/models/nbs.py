# Copyright (C) 2019  Renato Lima - Akretion
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import _, fields, models

from .ibpt import get_ibpt_service


class Nbs(models.Model):
    _name = "l10n_br_fiscal.nbs"
    _inherit = [
        "l10n_br_fiscal.data.ncm.nbs.abstract",
        "mail.thread",
        "mail.activity.mixin",
    ]
    _description = "NBS"

    code = fields.Char(size=12)

    code_unmasked = fields.Char(size=10)

    tax_estimate_ids = fields.One2many(inverse_name="nbs_id")

    product_tmpl_ids = fields.One2many(inverse_name="nbs_id")

    _sql_constraints = [
        (
            "fiscal_nbs_code_uniq",
            "unique (code)",
            _("NBS already exists with this code !"),
        )
    ]

    def _get_ibpt(self, config, code_unmasked):
        return get_ibpt_service(config, code_unmasked)
