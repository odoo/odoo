# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging

from collections import defaultdict
from datetime import timedelta
from itertools import groupby

from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import (
    AccessError,
    RedirectWarning,
    UserError,
    ValidationError,
)
from odoo.fields import Command
from odoo.http import request
from odoo.osv import expression
from odoo.tools import (
    create_index,
    float_is_zero,
    format_amount,
    format_date,
    is_html_empty,
    SQL,
    formatLang,
)
from odoo.tools.mail import html_keep_url

from odoo.addons.payment import utils as payment_utils

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    #===CUSTOM CHILD OF COMPUTE METHODS ===#

    def _confirmation_error_message(self):
        super()._confirmation_error_message()

        if self.partner_credit_warning != '':
            return _(
                "Total credit of %(partner_name)s exceeds its credit limit of %(credit_limit)s, you cannot confirm it.", 
                partner_name = self.partner_id.name, 
                credit_limit = formatLang(self.env, 
                                          self.partner_id.credit_limit, 
                                          currency_obj = self.company_id.currency_id)
                )
            
        

