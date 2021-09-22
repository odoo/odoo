# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_in_shipping_gstin = fields.Char("Shipping GSTIN")

    @api.constrains('l10n_in_shipping_gstin')
    def _check_l10n_in_shipping_gstin(self):
        check_vat_in = self.env['res.partner'].check_vat_in
        wrong_shipping_gstin_partner = self.filtered(lambda p: p.l10n_in_shipping_gstin and not check_vat_in(p.l10n_in_shipping_gstin))
        if wrong_shipping_gstin_partner:
            raise ValidationError(_("The shipping GSTIN number [%s] does not seem to be valid") %(",".join(p.l10n_in_shipping_gstin for p in wrong_shipping_gstin_partner)))
