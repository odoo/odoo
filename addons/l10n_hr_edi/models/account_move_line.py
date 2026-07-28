from odoo import api, models, fields
from odoo.tools.sql import column_exists, create_column


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    l10n_hr_kpd_category_id = fields.Many2one(
        comodel_name='l10n_hr.kpd.category',
        string="KPD category",
        compute='_compute_l10n_hr_product_id_kpd',
        store=True,
        readonly=False,
    )

    @api.depends('product_id')
    def _compute_l10n_hr_product_id_kpd(self):
        """Copy KPD code from product template when a product is selected for the line."""
        for line in self:
            if line.product_id:
                line.l10n_hr_kpd_category_id = line.product_id.l10n_hr_kpd_category_id

    def _auto_init(self):
        if not column_exists(self.env.cr, 'account_move_line', 'l10n_hr_kpd_category_id'):
            create_column(self.env.cr, 'account_move_line', 'l10n_hr_kpd_category_id', 'integer')
        return super()._auto_init()
