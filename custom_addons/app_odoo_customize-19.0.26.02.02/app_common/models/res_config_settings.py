# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    app_saas_ok = fields.Boolean(
        'Enable managed services',
        default=False,
        config_parameter='app_saas_ok',
        help="Reserved toggle for future Kodoo-managed services."
    )
