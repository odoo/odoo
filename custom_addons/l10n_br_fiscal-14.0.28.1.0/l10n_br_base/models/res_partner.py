# Copyright (C) 2009 Gabriel C. Stabel
# Copyright (C) 2009 Renato Lima (Akretion)
# Copyright (C) 2012 Raphaël Valyi (Akretion)
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html


from erpbrasil.base.fiscal import cnpj_cpf

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from ..tools import check_cnpj_cpf, check_ie


class Partner(models.Model):
    _name = "res.partner"
    _inherit = [_name, "l10n_br_base.party.mixin"]

    vat = fields.Char(compute="_compute_vat_from_cnpj_cpf", store=True)

    is_accountant = fields.Boolean(string="Is accountant?")

    crc_code = fields.Char(string="CRC Code", size=18)

    crc_state_id = fields.Many2one(comodel_name="res.country.state", string="CRC State")

    rntrc_code = fields.Char(string="RNTRC Code", size=12)

    cei_code = fields.Char(string="CEI Code", size=12)

    union_entity_code = fields.Char(string="Union Entity code")

    pix_key_ids = fields.One2many(
        string="Pix Keys",
        comodel_name="res.partner.pix",
        inverse_name="partner_id",
        help="Keys for Brazilian instant payment (pix)",
    )

    show_l10n_br = fields.Boolean(
        compute="_compute_show_l10n_br",
        help="Indicates if Brazilian localization fields should be displayed.",
    )

    @api.constrains("cnpj_cpf", "inscr_est")
    def _check_cnpj_inscr_est(self):
        for record in self:
            domain = []

            # permite cnpj vazio
            if not record.cnpj_cpf:
                return

            if self.env.context.get("disable_allow_cnpj_multi_ie"):
                return

            allow_cnpj_multi_ie = (
                record.env["ir.config_parameter"]
                .sudo()
                .get_param("l10n_br_base.allow_cnpj_multi_ie", default=True)
            )

            if record.parent_id:
                domain += [
                    ("id", "not in", record.parent_id.ids),
                    ("parent_id", "not in", record.parent_id.ids),
                ]

            domain += [("cnpj_cpf", "=", record.cnpj_cpf), ("id", "!=", record.id)]

            # se encontrar CNPJ iguais
            if record.env["res.partner"].search(domain):
                if cnpj_cpf.validar_cnpj(record.cnpj_cpf):
                    if allow_cnpj_multi_ie == "True":
                        for partner in record.env["res.partner"].search(domain):
                            if (
                                partner.inscr_est == record.inscr_est
                                and not record.inscr_est
                            ):
                                raise ValidationError(
                                    _(
                                        "There is already a partner record with this "
                                        "Estadual Inscription !"
                                    )
                                )
                    else:
                        raise ValidationError(
                            _("There is already a partner record with this CNPJ !")
                        )
                else:
                    raise ValidationError(
                        _("There is already a partner record with this CPF/RG!")
                    )

    @api.depends(
        "cnpj_cpf", "is_company", "parent_id", "parent_id.vat", "commercial_partner_id"
    )
    def _compute_vat_from_cnpj_cpf(self):
        for partner in self:
            if partner.company_name and partner.vat:
                continue
            elif partner.commercial_partner_id.cnpj_cpf:
                partner.vat = partner.commercial_partner_id.cnpj_cpf
            elif partner.vat:
                continue
            else:
                partner.vat = False

    @api.constrains("cnpj_cpf", "country_id")
    def _check_cnpj_cpf(self):
        for record in self:
            check_cnpj_cpf(
                record.env,
                record.cnpj_cpf,
                record.country_id,
            )

    @api.constrains("inscr_est", "state_id", "is_company")
    def _check_ie(self):
        """Checks if company register number in field insc_est is valid,
        this method call others methods because this validation is State wise

        :Return: True or False.
        """
        for record in self:
            if record.is_company:
                check_ie(
                    record.env, record.inscr_est, record.state_id, record.country_id
                )

    @api.constrains("state_tax_number_ids")
    def _check_state_tax_number_ids(self):
        """Checks if field other insc_est is valid,
        this method call others methods because this validation is State wise
        :Return: True or False.
        """
        for record in self:
            for inscr_est_line in record.state_tax_number_ids:
                check_ie(
                    record.env,
                    inscr_est_line.inscr_est,
                    inscr_est_line.state_id,
                    record.country_id,
                )

                if inscr_est_line.state_id.id == record.state_id.id:
                    raise ValidationError(
                        _(
                            "There can only be one state tax"
                            " number per state for each partner!"
                        )
                    )
                duplicate_ie = record.search(
                    [
                        ("state_id", "=", inscr_est_line.state_id.id),
                        ("inscr_est", "=", inscr_est_line.inscr_est),
                    ]
                )
                if duplicate_ie:
                    raise ValidationError(
                        _("State Tax Number already used {}").format(duplicate_ie.name)
                    )

    @api.model
    def _address_fields(self):
        """Returns the list of address
        fields that are synced from the parent."""
        return super()._address_fields() + ["district"]

    @api.onchange("city_id")
    def _onchange_city_id(self):
        self.city = self.city_id.name

    def _compute_show_l10n_br(self):
        """
        Defines when Brazilian localization fields should be displayed.
        """
        for rec in self:
            if rec.company_id and rec.company_id.country_id != self.env.ref("base.br"):
                rec.show_l10n_br = False
            else:
                rec.show_l10n_br = True

    def create_company(self):
        self.ensure_one()
        inscr_est = self.inscr_est
        inscr_mun = self.inscr_mun
        res = super().create_company()
        if res:
            parent = self.parent_id
            if parent.country_id.code == "BR":
                parent.legal_name = parent.name
                parent.cnpj_cpf = parent.vat
                parent.inscr_est = inscr_est
                parent.inscr_mun = inscr_mun
        return res
