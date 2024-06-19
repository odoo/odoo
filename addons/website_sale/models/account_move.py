# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.sql import column_exists, create_column


class AccountMove(models.Model):
    _inherit = 'account.move'

    website_id = fields.Many2one(
        'website', compute='_compute_website_id', string='Website',
        help='Website through which this invoice was created for eCommerce orders.',
        store=True, readonly=True, tracking=True)

    def _auto_init(self):
        if not column_exists(self.env.cr, "account_move", "website_id"):
            # Creating the column via `_auto_init` prevents a MemoryError in databases where many
            # invoices exist when `website_sale` is installed, as it skips the computation of the
            # `website_id` field.
            create_column(self.env.cr, "account_move", "website_id", "int4")
        super()._auto_init()

    def preview_invoice(self):
        action = super().preview_invoice()
        if action['url'].startswith('/'):
            # URL should always be relative, safety check
            action['url'] = f'/@{action["url"]}'
        return action

    @api.depends('partner_id')  # Dummy depends to trigger compute, will be dropped in master
    def _compute_website_id(self):
        for move in self:
            source_websites = move.line_ids.sale_line_ids.order_id.website_id
            if len(source_websites) == 1:
                move.website_id = source_websites
            else:
                move.website_id = False
