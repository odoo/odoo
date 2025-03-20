# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime
from odoo import api, fields, models, SUPERUSER_ID, _


class StockLot(models.Model):
    _inherit = 'stock.lot'

    use_expiration_date = fields.Boolean(
        string='Use Expiration Date', related='product_id.use_expiration_date')
    expiration_date = fields.Datetime(
        string='Expiration Date', compute='_compute_expiration_date', store=True, readonly=False,
        help='This is the date on which the goods with this Serial Number may become dangerous and must not be consumed.')
    use_date = fields.Datetime(string='Best before Date', compute='_compute_dates', store=True, readonly=False,
        help='This is the date on which the goods with this Serial Number start deteriorating, without being dangerous yet.')
    removal_date = fields.Datetime(string='Removal Date', compute='_compute_dates', store=True, readonly=False,
        help='This is the date on which the goods with this Serial Number should be removed from the stock and not be counted in the Fresh On Hand Stock anymore. This date will be used in FEFO removal strategy.')
    alert_date = fields.Datetime(string='Alert Date', compute='_compute_dates', store=True, readonly=False,
        help='Date to determine the expired lots and serial numbers using the filter "Expiration Alerts".')
    product_expiry_alert = fields.Boolean(compute='_compute_product_expiry_alert', help="The Expiration Date has been reached.")
    product_expiry_reminded = fields.Boolean(string="Expiry has been reminded")

    @api.depends('use_expiration_date', 'expiration_date', 'alert_date')
    @api.depends_context('formatted_display_name')
    def _compute_display_name(self):
        lots_to_process_ids = []
        for lot in self:
            if lot.env.context.get('formatted_display_name') and lot.use_expiration_date and lot.expiration_date:
                name = f"{lot.name}"
                if fields.Datetime.now() >= lot.expiration_date:
                    name += self.env._("\t--Expired--")
                elif lot.alert_date and fields.Datetime.now() >= lot.alert_date:
                    name += self.env._("\t--Expire on %(date)s--", date=fields.Datetime.to_string(lot.expiration_date))
                lot.display_name = name
            else:
                lots_to_process_ids.append(lot.id)
        if lots_to_process_ids:
            super(StockLot, self.env['stock.lot'].browse(lots_to_process_ids))._compute_display_name()

    @api.depends('expiration_date')
    def _compute_product_expiry_alert(self):
        current_date = fields.Datetime.now()
        for lot in self:
            if lot.expiration_date:
                lot.product_expiry_alert = lot.expiration_date <= current_date
            else:
                lot.product_expiry_alert = False

    @api.depends('product_id')
    def _compute_expiration_date(self):
        self.expiration_date = False
        for lot in self:
            if lot.product_id.use_expiration_date and not lot.expiration_date:
                duration = lot.product_id.product_tmpl_id.expiration_time
                lot.expiration_date = datetime.datetime.now() + datetime.timedelta(days=duration)

    @api.depends('product_id', 'expiration_date')
    def _compute_dates(self):
        for lot in self:
            if not lot.product_id.use_expiration_date:
                lot.use_date = False
                lot.removal_date = False
                lot.alert_date = False
            elif lot.expiration_date:
                # when create
                if lot.product_id != lot._origin.product_id or \
                   (not lot.use_date and not lot.removal_date and not lot.alert_date) or \
                   (lot.expiration_date and not lot._origin.expiration_date):
                    product_tmpl = lot.product_id.product_tmpl_id
                    lot.use_date = lot.expiration_date - datetime.timedelta(days=product_tmpl.use_time)
                    lot.removal_date = lot.expiration_date - datetime.timedelta(days=product_tmpl.removal_time)
                    lot.alert_date = lot.expiration_date - datetime.timedelta(days=product_tmpl.alert_time)
                # when change
                elif lot._origin.expiration_date:
                    time_delta = lot.expiration_date - lot._origin.expiration_date
                    lot.use_date = lot._origin.use_date and lot._origin.use_date + time_delta
                    lot.removal_date = lot._origin.removal_date and lot._origin.removal_date + time_delta
                    lot.alert_date = lot._origin.alert_date and lot._origin.alert_date + time_delta

    @api.model
    def _alert_date_exceeded(self):
        """Log an activity on internally stored lots whose alert_date has been reached.

        No further activity will be generated on lots whose alert_date
        has already been reached (even if the alert_date is changed).
        """
        alert_lots = self.env['stock.lot'].search([
            ('alert_date', '<=', fields.Date.today()),
            ('product_expiry_reminded', '=', False)])

        lot_stock_quants = self.env['stock.quant'].search([
            ('lot_id', 'in', alert_lots.ids),
            ('quantity', '>', 0),
            ('location_id.usage', '=', 'internal')])
        alert_lots = lot_stock_quants.mapped('lot_id')

        for lot in alert_lots:
            lot.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=lot.product_id.with_company(lot.company_id).responsible_id.id or lot.product_id.responsible_id.id or SUPERUSER_ID,
                note=_("The alert date has been reached for this lot/serial number"),
                summary=_("Alert Date Reached"),
            )
        alert_lots.write({
            'product_expiry_reminded': True
        })
