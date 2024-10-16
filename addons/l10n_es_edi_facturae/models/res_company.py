from odoo import fields, models
from odoo.addons import l10n_es


class ResCompany(l10n_es.ResCompany):

    l10n_es_edi_facturae_residence_type = fields.Char(string='Facturae EDI Residency Type Code', related='partner_id.l10n_es_edi_facturae_residence_type')
    l10n_es_edi_facturae_certificate_ids = fields.One2many(string='Facturae EDI signing certificate',
        comodel_name='certificate.certificate', inverse_name='company_id', domain=[('scope', '=', 'facturae')])
