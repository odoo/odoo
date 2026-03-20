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
            if location.is_subcontract() and location.usage != 'internal':
                raise ValidationError(_("In order to manage stock accurately, subcontracting locations must be type Internal, linked to the appropriate company."))

    def _check_access_putaway(self):
        """ Use sudo mode for subcontractor """
        if self.env.user.partner_id.is_subcontractor:
            return self.sudo()
        else:
            return super()._check_access_putaway()

    def is_subcontract(self):
        subcontracting_location = self.company_id.subcontracting_location_id
        return subcontracting_location and self._child_of(subcontracting_location)
