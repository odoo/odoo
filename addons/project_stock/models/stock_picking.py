# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import stock


class StockPicking(stock.StockPicking):

    project_id = fields.Many2one('project.project')
