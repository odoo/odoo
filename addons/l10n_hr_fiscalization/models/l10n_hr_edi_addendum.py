from odoo import fields, models


class L10nHrEdiAddendum(models.Model):
    _inherit = 'l10n_hr_edi.addendum'

    payment_method_type = fields.Selection(
        selection_add=[
            ('G', 'Gotovina'),   # Cash - direct fiscalization only
            ('K', 'Kartice'),    # Card - direct fiscalization only
        ],
    )
