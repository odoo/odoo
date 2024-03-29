from odoo import fields, models


class Company(models.Model):
    _inherit = 'res.company'

    l10n_es_edi_facturae_residence_type = fields.Char(string='Facturae EDI Residency Type Code', related='partner_id.l10n_es_edi_facturae_residence_type')
    l10n_es_edi_facturae_certificate_id = fields.One2many(string='Facturae EDI signing certificate',
        comodel_name='l10n_es_edi_facturae.certificate', inverse_name='company_id')
