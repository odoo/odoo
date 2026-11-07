from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_es_tbai_reversed_ids = fields.Many2many(
        'account.move', 'account_move_tbai_reversed_moves', 'refund_id', 'reversed_move_id',
        string="Refunded Invoices",
        domain="[('move_type', '=', 'in_invoice' if move_type == 'in_refund' else 'out_invoice'), ('commercial_partner_id', '=', commercial_partner_id)]",
        help="In the case where a refund has multiple original invoices, you can set them here. ",
    )