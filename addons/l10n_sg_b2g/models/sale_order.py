from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    l10n_sg_statutory_board_subbusiness_unit = fields.Many2one(
        'l10n.sg.statutory.board.subbusiness.unit',
        string='Sub-Business Unit',
        domain="[('statutory_board_id', 'parent_of', partner_id)]",
    )
    l10n_sg_partner_is_statutory_board = fields.Boolean(
        compute='_compute_l10n_sg_partner_is_statutory_board',
    )

    @api.depends('partner_id.commercial_partner_id.category_id')
    def _compute_l10n_sg_partner_is_statutory_board(self):
        statutory_board_tag = self.env.ref(
            'l10n_sg_b2g.res_partner_category_statutory_board',
            raise_if_not_found=False,
        )
        for order in self:
            commercial_partner_id = order.partner_id.commercial_partner_id
            order.l10n_sg_partner_is_statutory_board = (
                bool(statutory_board_tag and commercial_partner_id)
                and statutory_board_tag in commercial_partner_id.category_id
            )
