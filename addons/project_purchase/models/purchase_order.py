# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import purchase


class PurchaseOrder(purchase.PurchaseOrder):

    project_id = fields.Many2one('project.project')
