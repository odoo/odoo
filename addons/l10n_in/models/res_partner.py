# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Use in view attrs. Need to required state_id if Country is India.
    l10n_in_country_code = fields.Char(related="country_id.code", string="Country code")

    @api.constrains('vat', 'country_id')
    def l10n_in_check_vat(self):
        for partner in self.filtered(lambda p: p.commercial_partner_id.country_id.code == 'IN' and p.vat and len(p.vat) != 15):
            raise ValidationError(_('The GSTIN [%s] for partner [%s] should be 15 characters only.') % (partner.vat, partner.name))
