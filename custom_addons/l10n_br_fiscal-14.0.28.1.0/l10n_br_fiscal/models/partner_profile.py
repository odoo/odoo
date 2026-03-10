# Copyright (C) 2009 Renato Lima - Akretion <renato.lima@akretion.com.br>
# Copyright (C) 2014  KMEE - www.kmee.com.br
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from ..constants.fiscal import (
    NFE_IND_IE_DEST,
    NFE_IND_IE_DEST_DEFAULT,
    PUBLIC_ENTIRY_TYPE,
    TAX_FRAMEWORK,
    TAX_FRAMEWORK_NORMAL,
)


class PartnerProfile(models.Model):
    _name = "l10n_br_fiscal.partner.profile"
    _description = "Fiscal Partner Profile"

    code = fields.Char(size=16, required=True)

    name = fields.Char(size=64)

    is_company = fields.Boolean(string="Is Company?")

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

    default = fields.Boolean(string="Default Profile", default=True)

    ind_ie_dest = fields.Selection(
        selection=NFE_IND_IE_DEST,
        string="Contribuinte do ICMS",
        required=True,
        default=NFE_IND_IE_DEST_DEFAULT,
    )

    tax_framework = fields.Selection(
        selection=TAX_FRAMEWORK, default=TAX_FRAMEWORK_NORMAL
    )

    partner_ids = fields.One2many(
        comodel_name="res.partner", string="Partner", compute="_compute_partner_info"
    )

    partner_qty = fields.Integer(
        string="Partner Quantity", compute="_compute_partner_info"
    )

    tax_definition_ids = fields.One2many(
        comodel_name="l10n_br_fiscal.tax.definition",
        inverse_name="fiscal_profile_id",
        string="Tax Definition",
    )

    _sql_constraints = [
        (
            "fiscal_partner_profile_code_uniq",
            "unique (code)",
            "Fiscal Partner Profile already exists with this code !",
        )
    ]

    def _compute_partner_info(self):
        for record in self:
            partners = record.env["res.partner"].search(
                [
                    ("fiscal_profile_id", "=", record.id),
                    "|",
                    ("active", "=", False),
                    ("active", "=", True),
                ]
            )
            record.partner_ids = partners
            record.partner_qty = len(partners)

    @api.constrains("default", "is_company")
    def _check_default(self):
        for profile in self:
            if (
                len(
                    profile.search(
                        [
                            ("default", "=", "True"),
                            ("is_company", "=", profile.is_company),
                        ]
                    )
                )
                > 1
            ):
                raise ValidationError(
                    _(
                        "Mantenha apenas um tipo fiscal padrão"
                        " para Pessoa Física ou para Pessoa Jurídica!"
                    )
                )
            return True

    @api.onchange("is_company")
    def _onchange_is_company(self):
        if not self.is_company:
            self.tax_framework = False

    def action_view_partners(self):
        self.ensure_one()
        action = self.env.ref("base.action_partner_other_form").read()[0]
        action["domain"] = [("fiscal_profile_id", "=", self.id)]
        return action
