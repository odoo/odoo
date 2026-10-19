# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class IrAttachment(models.Model):

    _inherit = 'ir.attachment'

    # If attachment is a DeCA, it stores the picking id it belongs to
    l10n_es_deca_picking_id = fields.Many2one(
        comodel_name='stock.picking',
        string="DeCA picking",
        ondelete='cascade',
        index="btree_not_null"
    )
