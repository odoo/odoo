# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import re


class L10nLatamIdentificationType(models.Model):
    _name = 'l10n_latam.identification.type'
    _description = "Partner Identification Type for LATAM countries"
    _order = 'sequence'

    sequence = fields.Integer('Sequence')
    name = fields.Char('Name')
    short_code = fields.Char('Short Code')
    active = fields.Boolean('Active', default=True)
    is_vat = fields.Boolean('Corresponds to a VAT number')
    country_id = fields.Many2one('res.country')
    is_foreign = fields.Boolean('Is Foreign')
    inv_code = fields.Char('Code for Invoicing XML')

    def name_get(self):
        # Prefetch the fields used by the `name_get`, so `browse` doesn't fetch other fields
        self.read(['name', 'short_code'])
        return [(idtype.id, '%s%s' % (idtype.short_code and '%s - ' % idtype.shortcode or '', idtype.name))
                for idtype in self]