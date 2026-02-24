# -*- coding: utf-8 -*-

from odoo import fields, models


class StockMove(models.Model):
    _inherit = 'stock.move'
    _description = 'Stock Move'
    task_category = fields.Many2one('task.category', 'Task Category')


class StockLocation(models.Model):
    _inherit = 'stock.location'
    _description = 'Stock Location'

    project_id = fields.Many2one('project.project', 'Project')

