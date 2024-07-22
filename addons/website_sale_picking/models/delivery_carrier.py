# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _, api
from odoo.exceptions import ValidationError

from odoo.tools.misc import format_duration


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    # Onsite delivery means the client comes to a physical store to get the products himself.
    delivery_type = fields.Selection(selection_add=[
        ('onsite', 'Pickup in store')
    ], ondelete={'onsite': 'set default'})

    warehouse_ids = fields.Many2many('stock.warehouse', string='Stores')

    @api.constrains('warehouse_ids', 'company_id')
    def _check_warehouse_company(self):
        for dm in self:
            if dm.company_id and any(
                wh.company_id and dm.company_id != wh.company_id for wh in dm.warehouse_ids
            ):
                raise ValidationError(
                    _("The delivery method and warehouse must share the same company")
                )

    def _onsite_get_close_locations(self, order):
        close_locations = []

        for wh in self.warehouse_ids:
            location = wh.partner_id
            res = dict(
                id=location['id'],
                name=location['name'].title(),
                street=f"{location['street'].title()}",
                city=location.city.title(),
                zip_code=location.zip,
                country_code=location.country_code,
                latitude=location.partner_latitude,
                longitude=location.partner_longitude,
                warehouse_id=wh.id,
                additional_data={'is_cart_in_stock': order._is_cart_in_stock(wh.id)}
            )
            if wh.opening_hours:  # Format opening hours dict for location selector.
                opening_hours_dict = {str(i): [] for i in range(7)}
                for att in wh.opening_hours.attendance_ids:
                    if att.day_period != 'lunch':
                        opening_hours_dict[att.dayofweek].append(
                            f'{format_duration(att.hour_from)} - {format_duration(att.hour_to)}'
                        )
                res['opening_hours'] = opening_hours_dict
            else:
                res['opening_hours'] = {}
            close_locations.append(res)

        return close_locations

    def onsite_rate_shipment(self, order):
        """
        Required to show the price on the checkout page for the onsite delivery type
        """
        return {
            'success': True,
            'price': self.product_id.list_price,
            'error_message': False,
            'warning_message': False
        }

    def onsite_send_shipping(self, pickings):
        return [{
            'exact_price': p.carrier_id.fixed_price,
            'tracking_number': False
        } for p in pickings]

    def onsite_cancel_shipment(self, pickings):
        pass  # No need to communicate to an external service, however the method must exist so that cancel_shipment() works.

    def action_view_onsite_delivery_methods(self):
        """ If there is only one 'onsite' delivery method then open its form view else open a list
            view with all onsite delivery methods"""
        onsite_dms = self.env['delivery.carrier'].search([('delivery_type', '=', 'onsite')])
        if len(onsite_dms) == 1:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'delivery.carrier',
                'view_mode': 'form',
                'res_id': onsite_dms.id,
                }
        return {
            'type': 'ir.actions.act_window',
            'name': _("Delivery Methods"),
            'res_model': 'delivery.carrier',
            'view_mode': 'tree,form',
            'context': "{'search_default_delivery_type': 'onsite'}",
        }
