from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductProduct(models.Model):
    _inherit = "product.product"

    l10n_tr_gibp_number = fields.Char(
        string="GIBP Number", copy=False, index="btree_not_null"
    )

    @api.constrains("l10n_tr_gibp_number")
    def _check_l10n_tr_gibp_number(self):
        for record in self:
            if record.l10n_tr_gibp_number and len(record.l10n_tr_gibp_number) != 12:
                raise ValidationError(_("GIBP Number must be 12 digits long."))
