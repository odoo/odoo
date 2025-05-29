from odoo import models, api

class FiscalPrinterService(models.AbstractModel):
    _name = 'fiscal.printer.service'
    _description = 'Fiscal Printer Service'

    @api.model
    def print_invoice(self, invoice_data):
        # Code to send data to the fiscal printer
        pass
