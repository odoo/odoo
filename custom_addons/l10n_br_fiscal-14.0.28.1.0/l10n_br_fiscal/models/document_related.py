# Copyright (C) 2020  Renato Lima - Akretion <renato.lima@akretion.com.br>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from erpbrasil.base.fiscal import cnpj_cpf
from erpbrasil.base.fiscal.edoc import ChaveEdoc

from odoo import api, fields, models

from odoo.addons.l10n_br_base.tools import check_cnpj_cpf, check_ie

from ..constants.fiscal import (
    MODELO_FISCAL_CTE,
    MODELO_FISCAL_NFCE,
    MODELO_FISCAL_NFE,
    MODELO_FISCAL_NFSE,
)


class DocumentRelated(models.Model):
    _name = "l10n_br_fiscal.document.related"
    _description = "Fiscal Document Related"

    document_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.document", string="Fiscal Document", index=True
    )

    document_related_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.document",
        string="Fiscal Document Related",
        index=True,
    )

    document_type_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.document.type", string="Fiscal Document Type"
    )

    document_type_code = fields.Char(related="document_type_id.code")

    document_key = fields.Char(size=44)

    document_serie = fields.Char(string="Serie", size=12)

    document_number = fields.Char(string="Number", size=32)

    state_id = fields.Many2one(
        comodel_name="res.country.state",
        string="State",
        domain=[("country_id.code", "=", "BR")],
    )

    cnpj_cpf = fields.Char(string="CNPJ/CPF", size=18)

    cpfcnpj_type = fields.Selection(
        selection=[("cpf", "CPF"), ("cnpj", "CNPJ")],
        string="Type Doc Number",
        default="cnpj",
    )

    inscr_est = fields.Char(string="Inscr. Estadual/RG", size=16)

    document_date = fields.Date(string="Data")

    currency_id = fields.Many2one(
        comodel_name="res.currency",
        default=lambda self: self.env.company.currency_id,
    )
    document_total_weight = fields.Float(string="Peso Total")
    document_total_amount = fields.Monetary(
        string="Valor Total", currency_field="currency_id"
    )

    @api.constrains("document_key")
    def _check_key(self):
        for record in self:
            if not record.document_key:
                return
            if record.document_type_id.code in (
                MODELO_FISCAL_CTE,
                MODELO_FISCAL_NFCE,
                MODELO_FISCAL_NFE,
                MODELO_FISCAL_NFSE,
            ):
                ChaveEdoc(chave=record.document_key, validar=True)

    @api.constrains("cnpj_cpf")
    def _check_cnpj_cpf(self):
        for record in self:
            check_cnpj_cpf(record.env, record.cnpj_cpf, self.env.ref("base.br"))

    @api.constrains("inscr_est", "state_id")
    def _check_ie(self):
        for record in self:
            check_ie(
                record.env, record.inscr_est, record.state_id, self.env.ref("base.br")
            )

    @api.onchange("document_related_id")
    def _onchange_document_related_id(self):
        related = self.document_related_id
        if not related:
            return False

        self.document_type_id = related.document_type_id
        self.document_total_amount = related.amount_total
        self.document_total_weight = related.total_weight

        if related.document_type_id.electronic:
            self.document_key = related.document_key
            self.document_serie = False
            self.document_number = False
            self.state_id = False
            self.cnpj_cpf = False
            self.cpfcnpj_type = False
            self.document_date = False
            self.inscr_est = False

        if related.document_type_id.code in ("01", "04"):
            self.access_key = False
            self.document_serie = related.document_serie
            self.document_number = related.document_number
            self.state_id = (
                related.partner_id
                and related.partner_id.state_id
                and related.partner_id.state_id.id
                or False
            )

            self.cnpj_cpf = related.partner_id and related.partner_id.cnpj_cpf or False

            if related.partner_id.is_company:
                self.cpfcnpj_type = "cnpj"
            else:
                self.cpfcnpj_type = "cpf"

            self.document_date = related.document_date

        if related.document_type_id.code == "04":
            self.inscr_est = (
                related.partner_id and related.partner_id.inscr_est or False
            )

    @api.onchange("cnpj_cpf", "cpfcnpj_type")
    def _onchange_mask_cnpj_cpf(self):
        self.cnpj_cpf = cnpj_cpf.formata(str(self.cnpj_cpf))
