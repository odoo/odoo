# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import requests
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.loglevels import exception_to_unicode

_logger = logging.getLogger(__name__)


class User(models.Model):
    _inherit = 'res.users'

    calendar_provider_name = fields.Selection(
        string="Provider",
        help="The calendar provider to use with the calendar syncer",
        selection=[('none', "No Provider Set")],
        default='none',
        required=True
    )
