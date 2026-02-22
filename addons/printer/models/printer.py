from odoo import models, fields


class Printer(models.Model):
    _name = 'printer.printer'
    _description = 'External Printer'

    name = fields.Char(required=True)
    ip_address = fields.Char(required=True, string="IP Address")
    report_ids = fields.Many2many('ir.actions.report', string='Linked Reports')
