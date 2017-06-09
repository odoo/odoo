#	-*-	coding:	utf-8	-*-


from odoo import api, fields, models, _


from itertools import groupby
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare,DEFAULT_SERVER_DATETIME_FORMAT

####    Model for Advanced Stamped Receipt    #####
class SaleAdvanceStampedReceipt(models.Model):
    _name =	"sales.adv.stamp.receipt"
    _description = "Advance Stamped Receipt"
    _order = "date"

    contact = fields.Char(string='Phone Number', required=True)
    fax = fields.Char(string='Fax', required=True)
    date = fields.Datetime(string='Date', default=fields.Datetime.now)
    name = fields.Char(string='Name', required=True)
    amount = fields.Float(string='Amount (Rs)')
    bill_no =	fields.Char(string='Bill No.', required=True)
    bill_date = fields.Datetime(string='Bill Date', required=True)
    product_id = fields.Many2one('product.product', string='Product',select=True)
