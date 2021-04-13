# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResIdentityMixin(models.AbstractModel):
    _name = 'res.identity.mixin'
    _description = 'Identity Mixin'

    identity_id = fields.Many2one(
        'res.identity', 'Identity',
        auto_join=True, required=True, ondelete='restrict')

    @api.model_create_multi
    def create(self, values_list):
        # create all identities once
        identity_vals_list = [
            self._identity_filter_fields(values)
            for values in values_list
            if not values.get('identity_id')
        ]
        identities = self.env['res.identity'].sudo().create(identity_vals_list)
        identity_ids_iter = iter(identities.ids)

        # update vals list, keeping the order
        for values in values_list:
            if not values.get('identity_id'):
                values['identity_id'] = next(identity_ids_iter)

        records = super(ResIdentityMixin, self).create(values_list)

        for record in records.sudo():
            record.identity_id.partner_id = record.id

        return records

    def _identity_filter_fields(self, values):
        mapping = {'name': 'name', 'email': 'email', 'phone': 'phone', 'image_1920': 'avatar'}
        return dict(
            (mapping[fname], values.get(fname))
            for fname in values.keys()
            if fname in mapping.keys()
        )
