# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.tools.json import scriptsafe as json_safe
from odoo.exceptions import ValidationError


class ChooseDeliveryCarrier(models.TransientModel):
    _inherit = 'choose.delivery.carrier'

    shipping_zip = fields.Char(related='order_id.partner_shipping_id.zip')
    shipping_country_code = fields.Char(related='order_id.partner_shipping_id.country_id.code')

    is_mondialrelay = fields.Boolean(compute='_compute_is_mondialrelay')
    mondialrelay_last_selected = fields.Char(string="Last Relay Selected")
    mondialrelay_last_selected_id = fields.Char(compute='_compute_mr_last_selected_id')
    mondialrelay_brand = fields.Char(related='carrier_id.mondialrelay_brand')
    mondialrelay_colLivMod = fields.Char(related='carrier_id.mondialrelay_packagetype')
    mondialrelay_allowed_countries = fields.Char(compute='_compute_mr_allowed_countries')

    @api.depends('carrier_id')
    def _compute_is_mondialrelay(self):
        self.ensure_one()
        self.is_mondialrelay = self.carrier_id.product_id.default_code == "MR"

    @api.depends('carrier_id', 'order_id.partner_shipping_id')
    def _compute_mr_last_selected_id(self):
        self.ensure_one()
        if self.order_id.partner_shipping_id.is_mondialrelay:
            self.mondialrelay_last_selected_id = '%s-%s' % (
                self.shipping_country_code,
                self.order_id.partner_shipping_id.ref.lstrip('MR#'),
            )
        else:
            self.mondialrelay_last_selected_id = ''

    @api.depends('carrier_id')
    def _compute_mr_allowed_countries(self):
        self.ensure_one()
        self.mondialrelay_allowed_countries = ','.join(self.carrier_id.country_ids.mapped('code')).upper() or ''

    def button_confirm(self):
        if self.carrier_id.is_mondialrelay:
            if not self.mondialrelay_last_selected:
                raise ValidationError(_('Please, choose a Parcel Point'))
            data = json_safe.loads(self.mondialrelay_last_selected)
            partner_shipping = self.order_id.partner_id._mondialrelay_search_or_create({
                'id': data['id'],
                'name': data['name'],
                'street': data['street'],
                'street2': data['street2'],
                'zip': data['zip'],
                'city': data['city'],
                'country_code': data['country'][:2].lower(),
            })
            if partner_shipping != self.order_id.partner_shipping_id:
                self.order_id.partner_shipping_id = partner_shipping
                self.order_id.onchange_partner_shipping_id()

        return super().button_confirm()
