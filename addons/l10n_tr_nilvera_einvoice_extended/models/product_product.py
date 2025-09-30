from odoo import _, api, fields, models

from odoo.exceptions import ValidationError


class ProductProduct(models.Model):
    _inherit = "product.product"

    l10n_tr_ctsp_number = fields.Char(string="CTSP Number", copy=False, index="btree_not_null")

    @api.constrains("l10n_tr_ctsp_number")
    def _check_l10n_tr_ctsp_number(self):
        for record in self:
            if record.l10n_tr_ctsp_number and len(record.l10n_tr_ctsp_number) > 12:
                raise ValidationError(_("CTSP Number must be 12 digits or fewer."))
