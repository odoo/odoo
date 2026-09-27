from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Mirrors website_sale's `journal_id` related field so the simplified
    # journal can be configured per website from the Website settings.
    simplified_invoice_journal_id = fields.Many2one(
        related='website_id.simplified_invoice_journal_id',
        readonly=False,
    )
