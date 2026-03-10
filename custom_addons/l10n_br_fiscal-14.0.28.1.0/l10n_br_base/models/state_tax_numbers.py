# Copyright (C) 2018-Today - Akretion (<http://www.akretion.com>).
# @author Renato Lima - Akretion <renato.lima@akretion.com.br>
# @author Raphael Valyi - Akretion <raphael.valyi@akretion.com>
# @author Magno Costa - Akretion <magno.costa@akretion.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class StateTaxNumbers(models.Model):
    _name = "state.tax.numbers"
    _description = "State Tax Numbers"

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Partner",
        ondelete="cascade",
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        ondelete="cascade",
    )

    inscr_est = fields.Char(string="State Tax Number", size=16, required=True)

    state_id = fields.Many2one(
        comodel_name="res.country.state", string="State", required=True
    )

    _sql_constraints = [
        (
            "l10n_br_base_state_tax_numbers_id_uniq",
            "unique (state_id, partner_id)",
            "The Partner already has a State Tax Number for that State!",
        )
    ]
