from odoo import fields, models


class BrFgtsDarf(models.Model):
    _name = "br.fgts.darf"
    _description = "Resumo FGTS e DARF"

    payslip_run_id = fields.Many2one("hr.payslip.run", ondelete="cascade")
    company_id = fields.Many2one("res.company", required=True, ondelete="cascade")
    currency_id = fields.Many2one("res.currency", related="company_id.currency_id")
    period = fields.Date(required=True)
    valor_fgts = fields.Monetary(currency_field="currency_id")
    valor_inss = fields.Monetary(currency_field="currency_id")
    valor_irrf = fields.Monetary(currency_field="currency_id")
    guia_fgts_pdf = fields.Binary()
    darf_pdf = fields.Binary()

