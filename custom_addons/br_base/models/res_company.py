from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    cnpj = fields.Char(related="partner_id.cnpj_cpf", readonly=False)
    inscricao_estadual = fields.Char(related="partner_id.ie", readonly=False)
    certificado_id = fields.Many2one(
        "br.certificado",
        string="Certificado Digital",
        ondelete="set null",
    )

