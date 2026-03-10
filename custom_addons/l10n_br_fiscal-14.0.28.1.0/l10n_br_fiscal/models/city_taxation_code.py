# Copyright 2020 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class CityTaxationCode(models.Model):
    _name = "l10n_br_fiscal.city.taxation.code"
    _inherit = "l10n_br_fiscal.data.abstract"
    _description = "City Taxation Code"

    service_type_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.service.type",
        string="Service Type",
        domain=[("internal_type", "=", "normal")],
    )

    state_id = fields.Many2one(
        comodel_name="res.country.state",
        string="State",
        domain=[("country_id.code", "=", "BR")],
    )

    city_id = fields.Many2one(
        string="City",
        comodel_name="res.city",
        domain="[('state_id', '=', state_id)]",
    )

    cnae_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.cnae",
        string="CNAE Code",
    )

    tax_definition_ids = fields.Many2many(
        comodel_name="l10n_br_fiscal.tax.definition",
        relation="tax_definition_city_taxation_code_rel",
        column1="city_taxation_code_id",
        column2="tax_definition_id",
        readonly=True,
        string="Tax Definition",
    )
