# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime
from odoo import api, fields, models, SUPERUSER_ID, _


class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    use_expiration_date = fields.Boolean(
        string='Use Expiration Date', related='product_id.use_expiration_date')
    expiration_date = fields.Datetime(string='Expiration Date',
        help='This is the date on which the goods with this Serial Number may become dangerous and must not be consumed.')
    use_date = fields.Datetime(string='Best before Date',
        help='This is the date on which the goods with this Serial Number start deteriorating, without being dangerous yet.')
    removal_date = fields.Datetime(string='Removal Date',
        help='This is the date on which the goods with this Serial Number should be removed from the stock. This date will be used in FEFO removal strategy.')
    alert_date = fields.Datetime(string='Alert Date',
        help='Date to determine the expired lots and serial numbers using the filter "Expiration Alerts".')
    product_expiry_alert = fields.Boolean(compute='_compute_product_expiry_alert', help="The Expiration Date has been reached.")
    product_expiry_reminded = fields.Boolean(string="Expiry has been reminded")

    @api.depends('expiration_date')
    def _compute_product_expiry_alert(self):
        current_date = fields.Datetime.now()
        for lot in self:
            if lot.expiration_date:
                lot.product_expiry_alert = lot.expiration_date <= current_date
            else:
                lot.product_expiry_alert = False

    def _get_dates(self, product_id=None):
        """Returns dates based on number of days configured in current lot's product."""
        mapped_fields = {
            'use_date': 'use_time',
            'removal_date': 'removal_time',
            'alert_date': 'alert_time'
        }
        res = {}
        product = self.env['product.product'].browse(product_id) or self.product_id
        if product.use_expiration_date:
            expiration_date = datetime.datetime.now() + datetime.timedelta(days=product.expiration_time)
            res['expiration_date'] = fields.Datetime.to_string(expiration_date)
            for field in mapped_fields:
                duration = getattr(product, mapped_fields[field])
                date = expiration_date - datetime.timedelta(days=duration)
                res[field] = fields.Datetime.to_string(date)
        return res

    # Assign dates according to products data
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            dates = self._get_dates(vals.get('product_id') or self.env.context.get('default_product_id'))
            for d in dates:
                if not vals.get(d):
                    vals[d] = dates[d]
        return super().create(vals_list)

    @api.onchange('expiration_date')
    def _onchange_expiration_date(self):
        if not self._origin or not (self.expiration_date and self._origin.expiration_date):
            return
        time_delta = self.expiration_date - self._origin.expiration_date
        # As we compare expiration_date with _origin.expiration_date, we need to
        # use `_get_date_values` with _origin to keep a stability in the values.
        # Otherwise it will recompute from the updated values if the user calls
        # this onchange multiple times without save between each onchange.
        vals = self._origin._get_date_values(time_delta, self.expiration_date)
        self.update(vals)

    @api.onchange('product_id')
    def _onchange_product(self):
        dates_dict = self._get_dates()
        for field, value in dates_dict.items():
            setattr(self, field, value)

    @api.model
    def _alert_date_exceeded(self):
        """Log an activity on internally stored lots whose alert_date has been reached.

        No further activity will be generated on lots whose alert_date
        has already been reached (even if the alert_date is changed).
        """
        alert_lots = self.env['stock.production.lot'].search([
            ('alert_date', '<=', fields.Date.today()),
            ('product_expiry_reminded', '=', False)])

        lot_stock_quants = self.env['stock.quant'].search([
            ('lot_id', 'in', alert_lots.ids),
            ('quantity', '>', 0),
            ('location_id.usage', '=', 'internal')])
        alert_lots = lot_stock_quants.mapped('lot_id')

        for lot in alert_lots:
            lot.activity_schedule(
                'product_expiry.mail_activity_type_alert_date_reached',
                user_id=lot.product_id.with_company(lot.company_id).responsible_id.id or lot.product_id.responsible_id.id or SUPERUSER_ID,
                note=_("The alert date has been reached for this lot/serial number")
            )
        alert_lots.write({
            'product_expiry_reminded': True
        })

    def _update_date_values(self, new_date):
        if new_date:
            time_delta = new_date - (self.expiration_date or fields.Datetime.now())
            vals = self._get_date_values(time_delta, new_date)
            vals['expiration_date'] = new_date
            self.write(vals)

    def _get_date_values(self, time_delta, new_date=False):
        ''' Return a dict with different date values updated depending of the
        time_delta. Used in the onchange of `expiration_date` and when user
        defines a date at the receipt. '''
        vals = {
            'use_date': self.use_date and (self.use_date + time_delta) or new_date,
            'removal_date': self.removal_date and (self.removal_date + time_delta) or new_date,
            'alert_date': self.alert_date and (self.alert_date + time_delta) or new_date,
        }
        return vals


class ProcurementGroup(models.Model):
    _inherit = 'procurement.group'

    @api.model
    def _run_scheduler_tasks(self, use_new_cursor=False, company_id=False):
        super(ProcurementGroup, self)._run_scheduler_tasks(use_new_cursor=use_new_cursor, company_id=company_id)
        self.env['stock.production.lot']._alert_date_exceeded()
        if use_new_cursor:
            self.env.cr.commit()
