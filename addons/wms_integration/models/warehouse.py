# -*- coding: utf-8 -*-
import json

import requests

from odoo import _, fields, models
from odoo.exceptions import ValidationError, UserError
from odoo.tools import datetime
from odoo.tools.float_utils import float_compare


class Warehouse(models.Model):
    _inherit = "stock.warehouse"
    _description = "WMS Extension"

    wms_warehouse_id = fields.Char('wms_warehouse_id', index=True,
                                   required=False)