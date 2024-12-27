from odoo import models, fields, api
from ethiopian_date import EthiopianDateConverter
import logging
from datetime import datetime,date

_logger = logging.getLogger(__name__)

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    date_order = fields.Date(string='Order Date', required=True, readonly=False, index=True, copy=False, default=fields.Date.context_today)
    purchase_date_et = fields.Char(string='Purchase Date (ET)', readonly=False, compute='_compute_et_date', store=True)
   

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
                            order.purchase_date_et = f"{et_date.day:02d}/{et_date.month:02d}/{et_date.year}"
                        # If et_date is a tuple, access elements by index
                        elif isinstance(et_date, tuple):
                            order.purchase_date_et = f"{et_date[2]:02d}/{et_date[1]:02d}/{et_date[0]}"
                    else:
                        _logger.error("Unexpected return type from EthiopianDateConverter.date_to_ethiopian")
                        order.purchase_date_et = False
                    _logger.info(f"Computed Ethiopian date {order.purchase_date_et} from {order.date_order}")
                except Exception as e:
                    order.purchase_date_et = False
                    _logger.error(f"Error converting to Ethiopian date: {e}")
            else:
                order.purchase_date_et = False


    @api.onchange('purchase_date_et')
    def _onchange_purchase_date_et(self):
        for order in self:
            if order.purchase_date_et:
                try:
                    # Split and convert Ethiopian date to Gregorian
                    day, month, year = map(int, order.purchase_date_et.split('/'))
                    gregorian_date = EthiopianDateConverter.to_gregorian(year, month, day)
                    order.date_order = gregorian_date
                    _logger.info(f"Converted Ethiopian date {order.purchase_date_et} to Gregorian {gregorian_date}")
                except Exception as e:
                    _logger.error(f"Error converting Ethiopian date to Gregorian: {e}")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'date_order' in vals and isinstance(vals['date_order'], datetime):
                vals['date_order'] = vals['date_order'].date()
        return super(PurchaseOrder, self).create(vals_list)

    def write(self, vals):
        if 'date_order' in vals and isinstance(vals['date_order'], datetime):
            vals['date_order'] = vals['date_order'].date()
        return super(PurchaseOrder, self).write(vals)

    def _prepare_order_line_move(self, line, group_id=False):
        res = super(PurchaseOrder, self)._prepare_order_line_move(line, group_id)
        if res and 'date' in res:
            res['date'] = self.date_order
        return res

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    date_order = fields.Date(related='order_id.date_order', string='Order Date', store=True, index=True)

    @api.model
    def _prepare_purchase_order_line(self, product_id, product_qty, product_uom, company_id, supplier, po):
        res = super(PurchaseOrderLine, self)._prepare_purchase_order_line(product_id, product_qty, product_uom, company_id, supplier, po)
        if res and 'date_order' in res and isinstance(res['date_order'], datetime):
            res['date_order'] = res['date_order'].date()
        return res
