#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#    Thinkopen - Brasil
#    Copyright (C) Thinkopen Solutions (<http://www.thinkopensolutions.com.br>)
#    Akretion
#    Copyright (C) Akretion (<http://www.akretion.com>)
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import api, fields, models
from odoo.tools import config


class Company(models.Model):
    _name = "res.company"
    _inherit = [_name, "format.address.mixin", "l10n_br_base.party.mixin"]

    def _get_company_address_field_names(self):
        partner_fields = super()._get_company_address_field_names()
        return partner_fields + [
            "legal_name",
            "cnpj_cpf",
            "inscr_est",
            "inscr_mun",
            "district",
            "city_id",
            "suframa",
            "state_tax_number_ids",
        ]

    def _inverse_legal_name(self):
        """Write the l10n_br specific functional fields."""
        for company in self:
            company.partner_id.legal_name = company.legal_name

    def _inverse_district(self):
        """Write the l10n_br specific functional fields."""
        for company in self:
            company.partner_id.district = company.district

    def _inverse_cnpj_cpf(self):
        """Write the l10n_br specific functional fields."""
        for company in self:
            company.partner_id.cnpj_cpf = company.cnpj_cpf

    def _inverse_inscr_est(self):
        """Write the l10n_br specific functional fields."""
        for company in self:
            company.partner_id.inscr_est = company.inscr_est

    def _inverse_state(self):
        """Write the l10n_br specific functional fields."""
        for company in self:
            company.partner_id.state_id = company.state_id

    def _inverse_state_tax_number_ids(self):
        """Write the l10n_br specific functional fields."""
        for company in self:
            state_tax_number_ids = self.env["state.tax.numbers"]
            for ies in company.state_tax_number_ids:
                state_tax_number_ids |= ies
            company.partner_id.state_tax_number_ids = state_tax_number_ids

    def _inverse_inscr_mun(self):
        """Write the l10n_br specific functional fields."""
        for company in self:
            company.partner_id.inscr_mun = company.inscr_mun

    def _inverse_city_id(self):
        """Write the l10n_br specific functional fields."""
        for company in self:
            company.partner_id.city_id = company.city_id

    def _inverse_suframa(self):
        """Write the l10n_br specific functional fields."""
        for company in self:
            company.partner_id.suframa = company.suframa

    legal_name = fields.Char(
        compute="_compute_address",
        inverse="_inverse_legal_name",
    )

    district = fields.Char(
        compute="_compute_address",
        inverse="_inverse_district",
    )

    city_id = fields.Many2one(
        domain="[('state_id', '=', state_id)]",
        compute="_compute_address",
        inverse="_inverse_city_id",
    )

    country_id = fields.Many2one(default=lambda self: self.env.ref("base.br"))

    cnpj_cpf = fields.Char(
        compute="_compute_address",
        inverse="_inverse_cnpj_cpf",
    )

    inscr_est = fields.Char(
        compute="_compute_address",
        inverse="_inverse_inscr_est",
    )

    state_tax_number_ids = fields.One2many(
        string="State Tax Numbers",
        comodel_name="state.tax.numbers",
        inverse_name="company_id",
        compute="_compute_address",
        inverse="_inverse_state_tax_number_ids",
    )

    inscr_mun = fields.Char(
        compute="_compute_address",
        inverse="_inverse_inscr_mun",
    )

    suframa = fields.Char(
        compute="_compute_address",
        inverse="_inverse_suframa",
    )

    @api.model
    def _fields_view_get(
        self, view_id=None, view_type="form", toolbar=False, submenu=False
    ):
        res = super()._fields_view_get(view_id, view_type, toolbar, submenu)
        if view_type == "form":
            res["arch"] = self._fields_view_get_address(res["arch"])
        return res

    def write(self, values):
        try:
            result = super().write(values)
        except Exception as e:
            if not config["without_demo"] and values.get("currency_id"):
                # required for demo installation
                result = models.Model.write(self, values)
            else:
                raise e

        return result

    @api.onchange("state_id")
    def _onchange_state_id(self):
        res = super()._onchange_state_id()
        self.inscr_est = False
        self.partner_id.inscr_est = False
        self.partner_id.state_id = self.state_id
        return res
