# Copyright (C) 2015  Luis Felipe Miléo - KMEE
# Copyright (C) 2016  Renato Lima - Akretion
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import fields, models


class ResCountryState(models.Model):
    _inherit = "res.country.state"

    tax_definition_ids = fields.Many2many(
        comodel_name="l10n_br_fiscal.tax.definition",
        string="Tax Definitions",
        domain="['|', ('state_from_ids', '=', id), ('state_to_ids', '=', id)]",
    )
