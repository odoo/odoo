from odoo import models


class SpreadsheetDummy(models.Model):
    """ A very simple model only inheriting from spreadsheet.mixin to test
    its model functioning."""
    _description = 'Dummy Spreadsheet'
    _name = 'spreadsheet.test'
    _inherit = ['spreadsheet.mixin']
