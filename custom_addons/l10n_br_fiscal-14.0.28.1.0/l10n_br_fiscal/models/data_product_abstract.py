# Copyright (C) 2019  Renato Lima - Akretion <renato.lima@akretion.com.br>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import api, fields, models


class DataProductAbstract(models.AbstractModel):
    _name = "l10n_br_fiscal.data.product.abstract"
    _inherit = "l10n_br_fiscal.data.abstract"
    _description = "Fiscal Data Product Abstract"

    product_tmpl_ids = fields.One2many(
        comodel_name="product.template", string="Products", readonly=True
    )

    product_tmpl_qty = fields.Integer(
        string="Products Quantity", compute="_compute_product_tmpl_infos"
    )

    @api.depends("product_tmpl_ids")
    def _compute_product_tmpl_infos(self):
        for record in self:
            record.product_tmpl_qty = len(record.product_tmpl_ids)
