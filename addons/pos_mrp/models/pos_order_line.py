# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'
