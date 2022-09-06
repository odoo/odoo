from odoo import fields, models


class SpreadsheetDashboardGroup(models.Model):
    _name = 'spreadsheet.dashboard.group'
    _description = 'Group of dashboards'
    _order = 'sequence'

    name = fields.Char(required=True)
    dashboard_ids = fields.One2many('spreadsheet.dashboard', 'dashboard_group_id')
    sequence = fields.Integer()
