# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.partner'

    barcode = fields.Char(string='Barcode', help="BarCode", oldname='ean13')

    @api.model
    def create_from_ui(self, partner):
        """ create or modify a partner from the point of sale ui.
            partner contains the partner's fields. """
        # image is a dataurl, get the data after the comma
        if partner.get('image', False):
            img = partner['image'].split(',')[1]
            partner['image'] = img
        if partner.get('id', False):  # Modifying existing partner
            partner_id = partner['id']
            del partner['id']
            self.browse(partner_id).write(partner)
        else:
            partner_id = self.create(partner)
        return partner_id
