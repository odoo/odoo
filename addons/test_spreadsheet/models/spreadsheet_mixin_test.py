from odoo import models
from odoo.addons import spreadsheet


class SpreadsheetTest(models.Model, spreadsheet.SpreadsheetMixin):
    """ A very simple model only inheriting from spreadsheet.mixin to test
    its model functioning."""
    _description = 'Dummy Spreadsheet'
