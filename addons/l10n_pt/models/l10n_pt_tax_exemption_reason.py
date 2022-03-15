from odoo import models, fields


class TaxExemptionReason(models.Model):
    _name = 'l10n.pt.tax.exemption.reason'
    _description = 'Reasons why an item sale may be exempted from any tax according to ' \
                   'https://info.portaldasfinancas.gov.pt/pt/informacao_fiscal/codigos_tributarios/civa_rep/Pages/iva9.aspx'

    code = fields.Char('Code of the exemption reason', required=True)
    name = fields.Text('Name of the exemption reason', required=True)
