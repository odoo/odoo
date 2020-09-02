# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import models, api

_logger = logging.getLogger(__name__)

class MrpProduction(models.Model):
    _inherit = "mrp.production"

    @api.multi
    def _generate_moves(self):
        super(MrpProduction, self)._generate_moves()
        for production in self:
            _logger.info('%s', production.name)
            # Try to print product_type related field
            # It could raise a CacheMiss exception in some conditions
            for move in production.move_raw_ids:
                _logger.info('%s -> %s', production.name, move.product_type)

