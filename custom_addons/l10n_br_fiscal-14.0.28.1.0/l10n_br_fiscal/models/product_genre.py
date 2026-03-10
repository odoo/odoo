# Copyright (C) 2019 Renato Lima - Akretion <renato.lima@akretion.com.br>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import fields, models


class ProductGenre(models.Model):
    _name = "l10n_br_fiscal.product.genre"
    _inherit = "l10n_br_fiscal.data.product.abstract"
    _description = "Fiscal Fiscal Product Genre"

    product_tmpl_ids = fields.One2many(inverse_name="fiscal_genre_id")
