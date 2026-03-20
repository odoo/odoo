# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_mondialrelay = fields.Boolean(compute='_compute_is_mondialrelay')

    @api.depends('ref')
    def _compute_is_mondialrelay(self):
        for p in self:
            p.is_mondialrelay = p.ref and p.ref.startswith('MR#')

    @api.model
    def _mondialrelay_search_or_create(self, data):
        ref = 'MR#%s' % data['id']
        partner = self.search([
            ('id', 'child_of', self.commercial_partner_id.ids),
            ('ref', '=', ref),
            # fast check that address always the same
            ('street', '=', data['street']),
            ('zip', '=', data['zip']),
        ])
        if not partner:
            partner = self.create({
                'ref': ref,
                'name': data['name'],
                'street': data['street'],
                'street2': data['street2'],
                'zip': data['zip'],
                'city': data['city'],
                'country_id': self.env.ref('base.%s' % data['country_code']).id,
                'type': 'delivery',
                'parent_id': self.id,
            })
        return partner

    def _avatar_get_placeholder_path(self):
        if self.is_mondialrelay:
            return "delivery_mondialrelay/static/src/img/truck_mr.png"
        return super()._avatar_get_placeholder_path()

    def _can_be_edited_by_current_customer(self, **kwargs):
        return super()._can_be_edited_by_current_customer(**kwargs) and not self.is_mondialrelay
