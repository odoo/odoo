from odoo import fields, models


class PosPrinterIP(models.Model):
    _name = "pos.printer.ip"
    _description = "Stored POS Printer IP"

    name = fields.Char("IP Address", required=True)
