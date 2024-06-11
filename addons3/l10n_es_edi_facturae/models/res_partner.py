from odoo import api, fields, models


class Partner(models.Model):
    _inherit = 'res.partner'

    l10n_es_edi_facturae_residence_type = fields.Char(string='Facturae EDI Residency Type Code',
        compute='_compute_l10n_es_edi_facturae_residence_type', store=False, readonly=True,)

    @api.depends('country_id')
    def _compute_l10n_es_edi_facturae_residence_type(self):
        eu_country_ids = self.env.ref('base.europe').country_ids.ids
        for partner in self:
            country = partner.country_id
            if country.code == 'ES':
                partner.l10n_es_edi_facturae_residence_type = 'R'
            elif country.id in eu_country_ids:
                partner.l10n_es_edi_facturae_residence_type = 'U'
            else:
                partner.l10n_es_edi_facturae_residence_type = 'E'
