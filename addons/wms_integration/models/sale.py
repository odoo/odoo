# -*- coding: utf-8 -*-
import json

import requests

from odoo import _, fields, models
from odoo.exceptions import ValidationError, UserError
from odoo.tools import datetime
from odoo.tools.float_utils import float_compare


class SaleWMS(models.Model):
    _inherit = "sale.order"
    _description = "wms extetension methods sale"
    wms_order_id = fields.Char('wms_order_id', index=True,
                               required=False)
    wms_doc_number = fields.Char('wms_doc_number', index=True,
                                 required=False)
