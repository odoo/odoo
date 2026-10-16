from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    l10n_pk_is_fbr_3rd_schedule = fields.Boolean(
        string="Is FBR 3rd Schedule Product",
        help="Product taxed on its printed MRP under the FBR 3rd Schedule.",
    )

    @api.model
    def _load_pos_data_fields(self, config):
        result = super()._load_pos_data_fields(config)
        result += ['l10n_pk_is_fbr_3rd_schedule']
        return result
