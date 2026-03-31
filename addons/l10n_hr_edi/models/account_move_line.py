from odoo import api, models, fields


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    l10n_hr_kpd_category_id = fields.Many2one(
        comodel_name='l10n_hr.kpd.category',
        string="KPD category",
        compute='_compute_l10n_hr_product_id_kpd',
        store=True,
        readonly=False,
        init_column=lambda model: None,
    )

    @api.depends('product_id')
    def _compute_l10n_hr_product_id_kpd(self):
        """Copy KPD code from product template when a product is selected for the line."""
        for line in self:
            if line.product_id:
                line.l10n_hr_kpd_category_id = line.product_id.l10n_hr_kpd_category_id
