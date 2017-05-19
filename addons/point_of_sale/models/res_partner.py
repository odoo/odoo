# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    barcode = fields.Char(string='Barcode', oldname='ean13')
    pos_order_count = fields.Integer(
        compute='_compute_pos_order',
        help="The number of point of sales orders related to this customer",
        groups="point_of_sale.group_pos_user",
    )

    def _compute_pos_order(self):
        partners_data = self.env['pos.order'].read_group([('partner_id', 'in', self.ids)], ['partner_id'], ['partner_id'])
        mapped_data = dict([(partner['partner_id'][0], partner['partner_id_count']) for partner in partners_data])
        for partner in self:
            partner.pos_order_count = mapped_data.get(partner.id, 0)

    @api.model
    def create_from_ui(self, partner):
        """ create or modify a partner from the point of sale ui.
            partner contains the partner's fields. """
        # image is a dataurl, get the data after the comma
        if partner.get('image'):
            partner['image'] = partner['image'].split(',')[1]
        partner_id = partner.pop('id', False)
        if partner_id:  # Modifying existing partner
            self.browse(partner_id).write(partner)
        else:
            partner_id = self.create(partner).id
        return partner_id
