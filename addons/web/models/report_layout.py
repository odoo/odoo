# -*- coding: ascii -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class View(models.Model):
    _inherit = 'report.layout'
