from odoo import api, models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    l10n_hr_kpd_category_id = fields.Many2one(
        comodel_name='l10n_hr.kpd.category',
        string="KPD category",
    )


class L10nHrKpdCategory(models.Model):
    _name = 'l10n_hr.kpd.category'
    _description = 'Croatian KPD Category'
    _rec_names_search = ['name', 'description']

    name = fields.Char("Code", required=True)
    sector = fields.Char("Industry")
    description = fields.Char("Description")

    @api.depends('name', 'description')
    def _compute_display_name(self):
        for category in self:
            category.display_name = f'[{category.name}] {category.description}'
