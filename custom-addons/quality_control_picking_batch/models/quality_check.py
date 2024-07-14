# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class QualityCheck(models.Model):
    _inherit = "quality.check"

    batch_id = fields.Many2one(related='picking_id.batch_id')
