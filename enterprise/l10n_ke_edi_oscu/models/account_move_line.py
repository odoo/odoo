# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _compute_name(self):
        """ Compute overrides for quality-of-life when importing vendor bills.
            When importing vendor bills, most often the product won't be recognized.
            We override these computes so that the imported fields don't get
            overwritten with product defaults when the user selects the product.
        """
        not_ke_amls = self.filtered(lambda l: not l.move_id.l10n_ke_oscu_attachment_file)
        super(AccountMoveLine, not_ke_amls)._compute_name()

    def _compute_product_uom_id(self):
        not_ke_amls = self.filtered(lambda l: not l.move_id.l10n_ke_oscu_attachment_file)
        super(AccountMoveLine, not_ke_amls)._compute_product_uom_id()

    def _compute_price_unit(self):
        not_ke_amls = self.filtered(lambda l: not l.move_id.l10n_ke_oscu_attachment_file)
        super(AccountMoveLine, not_ke_amls)._compute_price_unit()

    def _compute_tax_ids(self):
        not_ke_amls = self.filtered(lambda l: not l.move_id.l10n_ke_oscu_attachment_file)
        super(AccountMoveLine, not_ke_amls)._compute_tax_ids()
