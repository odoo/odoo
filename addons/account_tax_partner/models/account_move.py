from odoo import models, fields


class AccountMove(models.Model):
    _inherit = "account.move"

    def get_taxes_values(self):
        """ We send invoice date to tax computation.
        TODO this should be improved on odoo core and make it cleaner
        """
        invoice_date = self.invoice_date or fields.Date.context_today(self)
        try:
            self.env.context.invoice_date = invoice_date
            self.env.context.invoice_company = self.company_id
        except Exception:
            pass
        return super().get_taxes_values()


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _compute_price(self):
        """ We send invoice date to tax computation.
        TODO this should be improved on odoo core and make it cleaner
        """
        invoice = self.move_id
        invoice_date = invoice.invoice_date or fields.Date.context_today(self)
        # hacemos try porque al llamarse desde acciones de servidor da error
        try:
            self.env.context.invoice_date = invoice_date
            self.env.context.invoice_company = self.company_id
        except Exception:
            pass
        return super()._compute_price()
