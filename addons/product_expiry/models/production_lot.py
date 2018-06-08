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


    def _alert_date_exceeded(self):
        # Run by a cron
        # if the alert_date is in the past, log a next activity on the next.production.lot 
        alert_lot_ids = self.env['stock.production.lot'].search([('alert_date', '<=', fields.Date.today())] )
        mail_activity_type =self.env.ref('product_expiry.mail_activity_alert_date_reached').id
        stock_quants = self.env['stock.quant'].search([
            ('lot_id', 'in', alert_lot_ids.ids),
            ('quantity', '>', 0)]).filtered(lambda quant: quant.location_id.usage == 'internal' )

        # only for the products that do not have already an activity
        stock_quants = stock_quants.filtered(lambda quant: 
            self.env['mail.activity'].search_count([
                ('res_model', '=', 'stock.production.lot'),
                ('res_id', '=', quant.lot_id.id),
                ('activity_type_id','=',mail_activity_type)]) == 0 )

        # when an activity is deleted, it goes into message
        stock_quants = stock_quants.filtered(lambda quant: 
            self.env['mail.message'].search_count([
                ('model', '=', 'stock.production.lot'),
                ('res_id', '=', quant.lot_id.id),
                ('subtype_id', '=', 3),
                ('mail_activity_type_id','=',mail_activity_type)]) == 0 )
        stock_quants.mapped('lot_id')._log_next_activity_alert_date_reached( 'The alert date has been reached for this lot/serial number' )
            
    def _log_next_activity_alert_date_reached(self, note):
        for lot in self:
            # If the user deleted todo activity type.
            try:
                activity_type_id =self.env.ref('product_expiry.mail_activity_alert_date_reached').id
            except:
                activity_type_id = False
            product_id = self.env['product.product'].search([('id', '=', lot.product_id._ids[0])])
            self.env['mail.activity'].create({
                'activity_type_id': activity_type_id,
                'note': note,
                'user_id': product_id.responsible_id.id,
                'res_model_id': self.env.ref('stock.model_stock_production_lot').id,
                'res_id': lot.id,
            })


class ProcurementGroup(models.Model):
    _inherit = 'procurement.group'

    @api.model
    def _run_scheduler_tasks(self, use_new_cursor=False, company_id=False):
        super(ProcurementGroup, self)._run_scheduler_tasks(use_new_cursor=use_new_cursor, company_id=company_id)
        self.env['stock.production.lot']._alert_date_exceeded()
        if use_new_cursor:
            self._cr.commit() 