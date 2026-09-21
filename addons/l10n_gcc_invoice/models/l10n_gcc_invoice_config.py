from odoo import fields, models


class L10nGccInvoiceConfig(models.Model):
    _name = "l10n_gcc_invoice.config"
    _description = "A company's l10n gcc invoice configuration"
    _inherit = ["mixin.company.config"]

    l10n_gcc_dual_language_invoice = fields.Boolean(string="GCC Formatted Invoices")
