from odoo import fields, models


class GreeceEDIDocument(models.Model):
    _inherit = 'l10n_gr_edi.document'

    state = fields.Selection(
        selection_add=[('delivery_note_pending', "Delivery note submission pending")],
        ondelete={'delivery_note_pending': 'cascade'},
    )
