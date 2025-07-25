# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models

from odoo.addons.l10n_my_edi.models.product_template import CLASSIFICATION_CODES_LIST


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    # ------------------
    # Fields declaration
    # ------------------

    l10n_my_edi_classification_code = fields.Selection(
        string="Malaysian classification code",
        selection=CLASSIFICATION_CODES_LIST,
        compute="_compute_l10n_my_edi_classification_code",
        store=True,
        readonly=False,
        copy=False,
    )

    # --------------------------------
    # Compute, inverse, search methods
    # --------------------------------

    @api.depends("product_id.product_tmpl_id")
    def _compute_l10n_my_edi_classification_code(self):
        """ Default to the product classification if any """
        for line in self:
            # We don't want to automatically update it on invoices that were sent to MyInvois
            if not line.move_id.l10n_my_edi_state:
                line.l10n_my_edi_classification_code = line.product_id.product_tmpl_id.l10n_my_edi_classification_code or line.l10n_my_edi_classification_code
