from odoo import models, fields, api
from ethiopian_date import EthiopianDateConverter
import logging
from datetime import date


_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    date_order = fields.Date(string='Order Date', required=True, readonly=False, index=True, copy=False,default=fields.Date.context_today)
    order_date_et = fields.Char(string='Order Date (ET)',readonly=False, compute='_compute_et_date', store=True)
    
    from datetime import date

    @api.depends('date_order')
    def _compute_et_date(self):
        for order in self:
            if order.date_order:
                try:
                    # Convert the Gregorian date to Ethiopian date
                    et_date = EthiopianDateConverter.date_to_ethiopian(order.date_order)
                    # Ensure the conversion returns a date object or tuple
                    if isinstance(et_date, (date, tuple)):
                        # If et_date is a date object, access attributes directly
                        if isinstance(et_date, date):
                            order.order_date_et = f"{et_date.day:02d}/{et_date.month:02d}/{et_date.year}"
                        # If et_date is a tuple, access elements by index
                        elif isinstance(et_date, tuple):
                            order.order_date_et = f"{et_date[2]:02d}/{et_date[1]:02d}/{et_date[0]}"
                    else:
                        _logger.error("Unexpected return type from EthiopianDateConverter.date_to_ethiopian")
                        order.order_date_et = False
                    _logger.info(f"Computed Ethiopian date {order.order_date_et} from {order.date_order}")
                except Exception as e:
                    order.order_date_et = False
                    _logger.error(f"Error converting to Ethiopian date: {e}")
            else:
                order.order_date_et = False

    @api.onchange('order_date_et')
    def _onchange_order_date_et(self):
        for order in self:
            if order.order_date_et:
                try:
                    day, month, year = map(int, order.order_date_et.split('/'))
                    gregorian_date = EthiopianDateConverter.to_gregorian(year, month, day)
                    order.date_order = gregorian_date
                except Exception as e:
                    _logger.error(f"Error converting Ethiopian date: {e}")
