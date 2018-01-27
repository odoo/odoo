# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime
from odoo import api, fields, models


class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    life_date = fields.Datetime(string='End of Life Date',
        help='This is the date on which the goods with this Serial Number may become dangerous and must not be consumed.')
    use_date = fields.Datetime(string='Best before Date',
        help='This is the date on which the goods with this Serial Number start deteriorating, without being dangerous yet.')
    removal_date = fields.Datetime(string='Removal Date',
        help='This is the date on which the goods with this Serial Number should be removed from the stock.')
    alert_date = fields.Datetime(string='Alert Date',
        help='Date to determine the expired lots and serial numbers using the filter "Expiration Alerts".')
    product_expiry_alert = fields.Boolean(compute='_compute_product_expiry_alert', help="The Alert Date has been reached.")

    @api.depends('alert_date')
    def _compute_product_expiry_alert(self):
        current_date = fields.Datetime.now()
        for lot in self.filtered(lambda l: l.alert_date):
            lot.product_expiry_alert = lot.alert_date <= current_date

    def _get_dates(self, product_id=None):
        """Returns dates based on number of days configured in current lot's product."""
        mapped_fields = {
            'life_date': 'life_time',
            'use_date': 'use_time',
            'removal_date': 'removal_time',
            'alert_date': 'alert_time'
        }
        res = dict.fromkeys(mapped_fields, False)
        product = self.env['product.product'].browse(product_id) or self.product_id
        if product:
            for field in mapped_fields:
                duration = getattr(product, mapped_fields[field])
                if duration:
                    date = datetime.datetime.now() + datetime.timedelta(days=duration)
                    res[field] = fields.Datetime.to_string(date)
        return res

    # Assign dates according to products data
    @api.model
    def create(self, vals):
        dates = self._get_dates(vals.get('product_id') or self.env.context.get('default_product_id'))
        for d in dates:
            if not vals.get(d):
                vals[d] = dates[d]
        return super(StockProductionLot, self).create(vals)

    @api.onchange('product_id')
    def _onchange_product(self):
        dates_dict = self._get_dates()
        for field, value in dates_dict.items():
            setattr(self, field, value)
