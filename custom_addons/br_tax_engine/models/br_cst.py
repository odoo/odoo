from odoo import fields, models


class BrCstIcms(models.Model):
    _name = "br.cst.icms"
    _description = "CST ICMS"
    _order = "code"

    code = fields.Char(required=True, size=3)
    name = fields.Char(required=True)
    tipo_tributacao = fields.Selection(
        [("tributado", "Tributado"), ("isento", "Isento"), ("nao_tributado", "Nao Tributado")],
        required=True,
    )
    date_from = fields.Date(required=True)
    date_to = fields.Date()


class BrCstPis(models.Model):
    _name = "br.cst.pis"
    _description = "CST PIS"
    _order = "code"

    code = fields.Char(required=True, size=2)
    name = fields.Char(required=True)
    tipo_tributacao = fields.Selection(
        [("tributado", "Tributado"), ("isento", "Isento"), ("nao_tributado", "Nao Tributado")],
        required=True,
    )
    date_from = fields.Date(required=True)
    date_to = fields.Date()


class BrCstCofins(models.Model):
    _name = "br.cst.cofins"
    _description = "CST COFINS"
    _order = "code"

    code = fields.Char(required=True, size=2)
    name = fields.Char(required=True)
    tipo_tributacao = fields.Selection(
        [("tributado", "Tributado"), ("isento", "Isento"), ("nao_tributado", "Nao Tributado")],
        required=True,
    )
    date_from = fields.Date(required=True)
    date_to = fields.Date()

