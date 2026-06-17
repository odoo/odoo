# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class L10nPhDiscountPrivilegeLineMixin(models.AbstractModel):
    """
    Shared logic for applying Philippine SC/PWD discount privileges on any
    document line (invoice lines, sale order lines, ...).

    Concrete models inherit this mixin and provide the model-specific
    hooks plus the correct dependencies for `_compute_l10n_ph_discount_amounts`.
    """

    _name = "l10n_ph.discount.privilege.line.mixin"
    _description = "Philippine Discount Privilege Line Mixin"

    currency_id = fields.Many2one("res.currency", string="Currency")

    l10n_ph_discount_privilege_id = fields.Many2one(
        "l10n_ph.discount.privilege",
        string="Discount Privilege",
        check_company=True,
        readonly=True,
        ondelete="restrict",
    )
    l10n_ph_original_tax_ids = fields.Many2many(
        "account.tax",
        string="Original Taxes (pre-privilege)",
        store=True,
    )
    l10n_ph_original_price_unit = fields.Float(
        string="Original Price Unit (pre-privilege)",
        digits="Product Price",
        store=True,
    )
    l10n_ph_original_discount = fields.Float(
        string="Original Discount (pre-privilege)",
        readonly=True,
    )
    l10n_ph_regular_discount_amount = fields.Monetary(
        string="Regular Disc. Amount",
        currency_field="currency_id",
        compute="_compute_l10n_ph_discount_amounts",
        readonly=True,
    )
    l10n_ph_special_discount_amount = fields.Monetary(
        string="Special Disc. Amount",
        currency_field="currency_id",
        compute="_compute_l10n_ph_discount_amounts",
        readonly=True,
    )

    # --- Model-specific hooks (overridden by each concrete model) ---

    def _l10n_ph_skip_discount_amounts(self):
        """
        Return True when the line should not receive privilege discount
        amounts (e.g. a section/note line, or a non-sale document).

        Must be overridden in each concrete model.
        """
        raise NotImplementedError

    def _l10n_ph_get_discount_price_details(self):
        """
        Return the gross (pre-discount) price amounts and the discount
        amounts derived from the current line.

        Concrete models must override this hook and return a 4-tuple:

        * ``gross_price_subtotal``: price subtotal before any discount.
        * ``subtotal_price_discount``: gross_price_subtotal - price_subtotal.
        * ``gross_price_total``: price total before any discount.
        * ``total_price_discount``: gross_price_total - price_total.
        """
        raise NotImplementedError

    # --- Discount amounts ---

    def _compute_l10n_ph_discount_amounts(self):
        """
        Compute l10n_ph_special_discount_amount and
        l10n_ph_regular_discount_amount for sale lines (SLSP/BOA reporting).

        Special (privileged lines): SC/PWD privileges are computed on the
        tax-excluded base (gross subtotal discount), while "special" discounts
        are computed on the tax-included base (gross total discount).

        Regular (non-privileged): explicit discount % back-computed from
        price_subtotal. Never reported as a privilege discount.
        """
        for line in self:
            if line._l10n_ph_skip_discount_amounts():
                line.l10n_ph_regular_discount_amount = 0.0
                line.l10n_ph_special_discount_amount = 0.0
                continue

            _, subtotal_price_discount, _, total_price_discount = line._l10n_ph_get_discount_price_details()
            privilege = line.l10n_ph_discount_privilege_id
            if privilege:
                line.l10n_ph_regular_discount_amount = 0.0
                if privilege.discount_type == "special":
                    line.l10n_ph_special_discount_amount = total_price_discount
                else:
                    line.l10n_ph_special_discount_amount = subtotal_price_discount
            else:
                line.l10n_ph_regular_discount_amount = subtotal_price_discount
                line.l10n_ph_special_discount_amount = 0.0

    # --- Preview helper for wizard ---

    def _l10n_ph_get_preview_discount_amount(self, privilege):
        """
        Return the discount amount that would apply to the line if the
        given privilege was applied.

        An empty privilege recordset is supported and yields 0.0.
        """
        self.ensure_one()
        if not privilege:
            return 0.0
        gross_price_subtotal, _, gross_price_total, _ = self._l10n_ph_get_discount_price_details()
        if privilege.discount_type == "special":
            return gross_price_total * privilege.discount_amount
        return gross_price_subtotal * privilege.discount_amount
