# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.osv import expression


class L10nLatamIdentificationType(models.Model):
    _name = 'l10n_latam.identification.type'
    _description = "Partner Identification Type for LATAM countries"
    _order = 'sequence'
    _rec_name = 'short_name'

    sequence = fields.Integer()
    name = fields.Char(translate=True, required=True,)
    short_name = fields.Char(translate=True, required=True,)
    active = fields.Boolean(default=True)
    country_id = fields.Many2one('res.country')

    # def name_get(self):
    #     # Prefetch the fields used by the `name_get`, so `browse` doesn't fetch other fields
    #     self.read(['name', 'short_name'])
    #     return [(idtype.id, '%s%s' % (idtype.short_name and '%s - ' % idtype.short_name or '', idtype.name))
    #             for idtype in self]

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            domain = [
                '|',
                ('short_name', '=ilike', name + '%'),
                ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&', '!'] + domain[1:]
        recs = self.search(domain + args, limit=limit)
        return recs.name_get()
