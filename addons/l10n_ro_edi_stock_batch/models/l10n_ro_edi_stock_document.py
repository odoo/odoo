from odoo import models, fields


class L10nRoEdiStockDocument(models.Model):
    _inherit = 'l10n_ro_edi.document'

    batch_id = fields.Many2one(comodel_name='stock.picking.batch')
