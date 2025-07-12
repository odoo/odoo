# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class StockLocation(models.Model):
    _inherit = 'stock.location'

    subcontractor_ids = fields.One2many('res.partner', 'property_stock_subcontractor')

    @api.constrains('usage', 'location_id')
    def _check_subcontracting_location(self):
        for location in self:
            if location == location.company_id.subcontracting_location_id:
                raise ValidationError(_("You cannot alter the company's subcontracting location"))

    def _check_access_putaway(self):
        """ Use sudo mode for subcontractor """
        if self.env.user.partner_id.is_subcontractor:
            return self.sudo()
        else:
            return super()._check_access_putaway()
