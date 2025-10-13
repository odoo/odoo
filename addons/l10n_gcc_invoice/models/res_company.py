from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_gcc_dual_language_invoice = fields.Boolean(string="GCC Formatted Invoices")
