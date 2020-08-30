# -*- coding: utf-8 -*-

import logging
from datetime import datetime, date, timedelta

from odoo import models, fields, api
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning


_logger = logging.getLogger(__name__)

class AccountAccount(models.Model):
    _inherit = 'account.account'

    depreciation = fields.Boolean(string="Depreciación")

    