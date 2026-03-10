# Copyright (C) 2019  Renato Lima - Akretion
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import _, fields, models


class TaxPisCofinsCredit(models.Model):
    _name = "l10n_br_fiscal.tax.pis.cofins.credit"
    _inherit = "l10n_br_fiscal.data.abstract"
    _description = "Tax PIS/COFINS Credit"

    code = fields.Char(size=3)

    _sql_constraints = [
        (
            "l10n_br_fiscal_tax_pis_cofins_credit_code_uniq",
            "unique (code)",
            _("Already exists with this code !"),
        )
    ]
