# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class ProductTemplate(models.Model):
    _inherit = "product.template"

    l10n_id_product_code = fields.Many2one(
        comodel_name="l10n_id_efaktur_coretax.product.code",
        compute="_compute_l10n_id_product_code",
        string="E-Faktur Product Code",
        store=True,
        readonly=False
    )

    @api.depends('type')
    def _compute_l10n_id_product_code(self):
        # used for setting default product code depending on product being goods/service
        # 000000 is default for both general goods/service
        for record in self:
            if record.type == 'service':
                record.l10n_id_product_code = self.env.ref('l10n_id_efaktur_coretax.product_code_000000_service', raise_if_not_found=False)
            else:
                record.l10n_id_product_code = self.env.ref('l10n_id_efaktur_coretax.product_code_000000_goods', raise_if_not_found=False)
