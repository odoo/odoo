# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    # ------------------
    # Fields declaration
    # ------------------

    l10n_cn_tax_category_id = fields.Many2one(
        string="Tax Category Code",
        comodel_name='l10n_cn_edi.tax.category',
        compute="_compute_l10n_cn_tax_category_id",
        store=True,
        readonly=False,
        copy=False,
    )

    # --------------------------------
    # Compute, inverse, search methods
    # --------------------------------

    @api.depends("product_id.product_tmpl_id")
    def _compute_l10n_cn_tax_category_id(self):
        """ Default to the product classification if any """
        for line in self:
            # TODO: check if we might not want to automatically update it on invoices that were sent to Baiwang?
            if not line.move_id.l10n_cn_baiwang_state:
                line.l10n_cn_tax_category_id = line.product_id.product_tmpl_id.l10n_cn_tax_category_id or line.l10n_cn_tax_category_id
