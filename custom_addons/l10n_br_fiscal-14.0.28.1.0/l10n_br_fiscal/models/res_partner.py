# Copyright (C) 2009 - TODAY Renato Lima - Akretion
# Copyright (C) 2020 - TODAY Luis Felipe Mileo - KMEE
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import api, fields, models

from ..constants.fiscal import (
    FINAL_CUSTOMER,
    FINAL_CUSTOMER_NO,
    NFE_IND_IE_DEST,
    NFE_IND_IE_DEST_9,
    NFE_IND_IE_DEST_DEFAULT,
    PUBLIC_ENTIRY_TYPE,
    TAX_FRAMEWORK,
    TAX_FRAMEWORK_NORMAL,
)


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def _default_fiscal_profile_id(self, is_company=False):
        """Define o valor padão para o campo tipo fiscal, por padrão pega
        o tipo fiscal para não contribuinte já que quando é criado um novo
        parceiro o valor do campo is_company é false"""
        return self.env["l10n_br_fiscal.partner.profile"].search(
            [("default", "=", True), ("is_company", "=", is_company)], limit=1
        )

    tax_framework = fields.Selection(
        selection=TAX_FRAMEWORK,
        default=TAX_FRAMEWORK_NORMAL,
        tracking=True,
    )

    legal_nature_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.legal.nature",
        string="Legal Nature",
    )

    cnae_main_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.cnae",
        domain=[("internal_type", "=", "normal")],
        string="Main CNAE",
    )

    cnae_secondary_ids = fields.Many2many(
        comodel_name="l10n_br_fiscal.cnae",
        domain="[('internal_type', '=', 'normal'), ('id', '!=', cnae_main_id)]",
        string="Secondary CNAEs",
    )

    ind_ie_dest = fields.Selection(
        selection=NFE_IND_IE_DEST,
        string="Contribuinte do ICMS",
        required=True,
        default=NFE_IND_IE_DEST_DEFAULT,
        tracking=True,
    )

    fiscal_profile_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.partner.profile",
        string="Fiscal Partner Profile",
        inverse="_inverse_fiscal_profile",
        domain="[('is_company', '=', is_company)]",
        default=_default_fiscal_profile_id,
        tracking=True,
    )

    is_public_entity = fields.Boolean(
        string="Public Entity",
        help="Indicates whether the entity in question is a "
        "public organization or government-related entity. It encompasses a "
        "range of entities such as municipal governments, state-owned "
        "enterprises (where the government is the largest shareholder), and "
        "other government-controlled organizations.",
    )

    public_entity_type = fields.Selection(
        selection=PUBLIC_ENTIRY_TYPE,
        string="Tipo de Entidade Governamental",
    )

    ind_final = fields.Selection(
        selection=FINAL_CUSTOMER,
        string="Final Consumption Operation",
        default=FINAL_CUSTOMER_NO,
        tracking=True,
    )

    cnpj_cpf = fields.Char(
        tracking=True,
    )

    inscr_est = fields.Char(
        tracking=True,
    )

    inscr_mun = fields.Char(
        tracking=True,
    )

    is_company = fields.Boolean(
        tracking=True,
    )

    state_id = fields.Many2one(
        tracking=True,
    )

    city_id = fields.Many2one(
        tracking=True,
    )

    is_anonymous_consumer = fields.Boolean(
        tracking=True,
        string="Anonymous Consumer",
    )

    nif_motive_absence = fields.Selection(
        selection=[
            ("0", "Not informed in the origin note"),
            ("1", "Exemption from NIF"),
            ("2", "NIF not required"),
        ],
        default=False,
        string="NIF motive absence",
    )

    def _inverse_fiscal_profile(self):
        for p in self:
            p._onchange_fiscal_profile_id()

    @api.onchange("is_company")
    def _onchange_is_company(self):
        for p in self:
            p.fiscal_profile_id = p._default_fiscal_profile_id(p.is_company)

    @api.onchange("fiscal_profile_id")
    def _onchange_fiscal_profile_id(self):
        for p in self:
            if p.fiscal_profile_id:
                p.tax_framework = p.fiscal_profile_id.tax_framework
                p.ind_ie_dest = p.fiscal_profile_id.ind_ie_dest
                p.is_public_entity = p.fiscal_profile_id.is_public_entity
                p.public_entity_type = p.fiscal_profile_id.public_entity_type

    @api.onchange("ind_ie_dest")
    def _onchange_ind_ie_dest(self):
        for p in self:
            if p.ind_ie_dest == NFE_IND_IE_DEST_9:
                p.inscr_est = False
                p.state_tax_number_ids = False

    @api.model
    def _commercial_fields(self):
        return super()._commercial_fields() + [
            "tax_framework",
            "cnae_main_id",
            "ind_ie_dest",
            "fiscal_profile_id",
            "ind_final",
            "inscr_est",
            "inscr_mun",
        ]
