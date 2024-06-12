# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    pos_order_count = fields.Integer(
        compute='_compute_pos_order',
        help="The number of point of sales orders related to this customer",
        groups="point_of_sale.group_pos_user",
    )
    pos_order_ids = fields.One2many('pos.order', 'partner_id', readonly=True)

    def _compute_pos_order(self):
        # retrieve all children partners and prefetch 'parent_id' on them
        all_partners = self.with_context(active_test=False).search_fetch(
            [('id', 'child_of', self.ids)],
            ['parent_id'],
        )
        pos_order_data = self.env['pos.order']._read_group(
            domain=[('partner_id', 'in', all_partners.ids)],
            groupby=['partner_id'], aggregates=['__count']
        )
        self_ids = set(self._ids)

        self.pos_order_count = 0
        for partner, count in pos_order_data:
            while partner:
                if partner.id in self_ids:
                    partner.pos_order_count += count
                partner = partner.parent_id

    def action_view_pos_order(self):
        '''
        This function returns an action that displays the pos orders from partner.
        '''
        action = self.env['ir.actions.act_window']._for_xml_id('point_of_sale.action_pos_pos_form')
        if self.is_company:
            action['domain'] = [('partner_id.commercial_partner_id', '=', self.id)]
        else:
            action['domain'] = [('partner_id', '=', self.id)]
        return action

    @api.model
    def create_from_ui(self, partner):
        """ create or modify a partner from the point of sale ui.
            partner contains the partner's fields. """
        # image is a dataurl, get the data after the comma
        if partner.get('image_1920'):
            partner['image_1920'] = partner['image_1920'].split(',')[1]
        partner_id = partner.pop('id', False)
        if partner_id:  # Modifying existing partner
            self.browse(partner_id).write(partner)
        else:
            partner_id = self.create(partner).id
        return partner_id
