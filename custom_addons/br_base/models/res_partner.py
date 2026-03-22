from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from ..services.br_cep_service import fetch_cep
from ..utils.br_document import (
    format_cnpj,
    format_cpf,
    strip_document,
    validate_cnpj,
    validate_cpf,
)


class ResPartner(models.Model):
    _inherit = "res.partner"

    cnpj_cpf = fields.Char(string="CNPJ/CPF", tracking=True)
    tipo_pessoa = fields.Selection(
        [("fisica", "Pessoa Fisica"), ("juridica", "Pessoa Juridica")],
        string="Tipo de Pessoa",
        default="juridica",
        tracking=True,
    )
    ie = fields.Char(string="Inscricao Estadual")
    im = fields.Char(string="Inscricao Municipal")
    municipio_id = fields.Many2one(
        "br.municipio",
        string="Municipio",
        ondelete="restrict",
    )

    @api.constrains("cnpj_cpf", "tipo_pessoa")
    def _check_cnpj_cpf(self):
        for partner in self:
            document = strip_document(partner.cnpj_cpf or "")
            if not document:
                continue
            if partner.tipo_pessoa == "juridica":
                if not validate_cnpj(document):
                    raise ValidationError(_("CNPJ invalido."))
            elif not validate_cpf(document):
                raise ValidationError(_("CPF invalido."))

    @api.onchange("cnpj_cpf", "tipo_pessoa")
    def _onchange_cnpj_cpf(self):
        for partner in self:
            document = strip_document(partner.cnpj_cpf or "")
            if not document:
                continue
            if partner.tipo_pessoa == "juridica" and len(document) == 14:
                partner.cnpj_cpf = format_cnpj(document)
            elif partner.tipo_pessoa == "fisica" and len(document) == 11:
                partner.cnpj_cpf = format_cpf(document)

    @api.onchange("zip")
    def _onchange_cep_br(self):
        for partner in self:
            cep = strip_document(partner.zip or "")
            if len(cep) != 8:
                continue
            payload = fetch_cep(cep)
            if not payload:
                return {
                    "warning": {
                        "title": _("CEP nao encontrado"),
                        "message": _("Nao foi possivel sugerir o endereco para o CEP informado."),
                    }
                }
            partner.street = payload.get("logradouro") or partner.street
            partner.city = payload.get("localidade") or partner.city
            uf = payload.get("uf")
            if uf:
                state = self.env["res.country.state"].search(
                    [("country_id.code", "=", "BR"), ("code", "=", uf)],
                    limit=1,
                )
                if state:
                    partner.state_id = state
            ibge = payload.get("ibge")
            if ibge:
                municipio = self.env["br.municipio"].search([("code_ibge", "=", ibge)], limit=1)
                if municipio:
                    partner.municipio_id = municipio

