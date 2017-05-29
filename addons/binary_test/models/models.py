# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class BinaryTest(models.Model):
    _name = 'binary_test.binary_test'

    name = fields.Char()
    value = fields.Binary()

    @api.onchange('name')
    def onchange_name(self):
        _logger.warning("The binary file is? ZZZ kB?: '%s'", self.value)
