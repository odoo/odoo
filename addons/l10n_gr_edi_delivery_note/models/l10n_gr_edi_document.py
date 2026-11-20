from odoo import fields, models


class GreeceEDIDocument(models.Model):
    _inherit = 'l10n_gr_edi.document'

    picking_id = fields.Many2one(comodel_name='stock.picking', ondelete='cascade', index='btree_not_null')
    state = fields.Selection(
        selection_add=[
            ('delivery_note_sent', "Delivery note sent"),
            ('delivery_note_error', "Delivery note send failed"),
        ],
        ondelete={
            'delivery_note_sent': 'cascade',
            'delivery_note_error': 'cascade',
        },
    )
