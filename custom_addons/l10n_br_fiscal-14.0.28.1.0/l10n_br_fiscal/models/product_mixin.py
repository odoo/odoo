# Copyright (C) 2021  Renato Lima - Akretion <renato.lima@akretion.com.br>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import api, models

from ..constants.fiscal import (
    NCM_FOR_SERVICE_REF,
    PRODUCT_FISCAL_TYPE_SERVICE,
    TAX_DOMAIN_ICMS,
    TAX_DOMAIN_ISSQN,
)


class ProductMixin(models.AbstractModel):
    _name = "l10n_br_fiscal.product.mixin"
    _description = "Fiscal Product Mixin"

    @api.onchange("fiscal_type")
    def _onchange_fiscal_type(self):
        for r in self:
            if r.fiscal_type == PRODUCT_FISCAL_TYPE_SERVICE:
                r.ncm_id = self.env.ref(NCM_FOR_SERVICE_REF)
                r.tax_icms_or_issqn = TAX_DOMAIN_ISSQN
            else:
                r.tax_icms_or_issqn = TAX_DOMAIN_ICMS

    @api.onchange("ncm_id")
    def _onchange_ncm_id(self):
        for r in self:
            if r.ncm_id:
                r.fiscal_genre_id = self.env["l10n_br_fiscal.product.genre"].search(
                    [("code", "=", r.ncm_id.code[0:2])]
                )

    @api.onchange("fiscal_genre_id")
    def _onchange_fiscal_genre_id(self):
        for r in self:
            if r.fiscal_genre_id and r.ncm_id:
                if r.fiscal_genre_id.code != r.ncm_id.code[0:2]:
                    r.ncm_id = False
