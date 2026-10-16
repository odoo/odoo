from odoo import fields, models


class L10n_Tr_EdiDocument(models.Model):
    _inherit = 'l10n_tr_edi.document'

    picking_id = fields.Many2one(
        comodel_name='stock.picking',
        index='btree_not_null',
        check_company=True,
        ondelete='cascade',
    )
    document_type = fields.Selection(
        selection_add=[('edispatch', "e-Dispatch"), ('edispatch_response', "e-Dispatch Response")],
        ondelete={'edispatch': 'cascade', 'edispatch_response': 'cascade'},
    )
