from odoo import models


class SpreadsheetTest(models.Model):
    """ A very simple model only inheriting from spreadsheet.mixin to test
    its model functioning."""
    _description = 'Dummy Spreadsheet'
    _inherit = ['spreadsheet.mixin']
