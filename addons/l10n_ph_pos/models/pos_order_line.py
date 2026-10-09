# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Command
from odoo.tools import float_compare, float_round

# ID holder information of an SC/PWD share, carried onto its invoice line.
HOLDER_FIELDS = (
    "l10n_ph_holder_partner_id",
    "l10n_ph_holder_name",
    "l10n_ph_holder_id_number",
    "l10n_ph_holder_representative_name",
    "l10n_ph_holder_representative_id",
)


class PosOrderLine(models.Model):
    _inherit = ["pos.order.line", "l10n_ph.discount.privilege.line.mixin"]
    _name = "pos.order.line"

    l10n_ph_original_tax_ids = fields.Many2many(
        relation="pos_order_line_l10n_ph_original_tax_rel",
    )
    # SC/PWD ID holder this share is attributed to. Their name and ID number
    # are taken from the contact, and recorded as presented at the time of
    # sale (BIR documentation): later changes to the contact don't alter them.
    l10n_ph_holder_partner_id = fields.Many2one(
        "res.partner",
        string="SC/PWD ID Holder Contact",
        index="btree_not_null",
    )
    l10n_ph_holder_name = fields.Char(string="SC/PWD ID Holder")
    l10n_ph_holder_id_number = fields.Char(string="SC/PWD ID Number")
    l10n_ph_holder_representative_name = fields.Char(
        string="SC/PWD Representative Name",
        help="Set when an authorized representative claims the discount on the "
        "ID holder's behalf (BIR RMC 71-2022).",
    )
    l10n_ph_holder_representative_id = fields.Char(string="SC/PWD Representative ID")
    l10n_ph_persons_sharing = fields.Integer(
        string="SC/PWD Persons Sharing",
        copy=False,
        help="Number of regular persons sharing this line's quantity, set on the "
        "regular share left by an SC/PWD discount privilege split. Any later "
        "split of this line pro-rates it among these persons only.",
    )
    l10n_ph_split_origin_line_id = fields.Many2one(
        "pos.order.line",
        string="SC/PWD Split From",
        copy=False,
        index="btree_not_null",
        help="Line this ID holder share was split off by an SC/PWD discount "
        "privilege split. Its ID holder already has their share of that line, "
        "and gets it back if the privilege is removed.",
    )

    @api.constrains("discount", "l10n_ph_discount_privilege_id")
    def _check_l10n_ph_no_double_discount(self):
        # SC/PWD privileges can't be combined with any other discount (RA 9994,
        # RA 10754): a privileged share is discounted by its privilege only.
        for line in self.filtered("l10n_ph_discount_privilege_id"):
            privilege_discount = line.l10n_ph_discount_privilege_id.discount_amount * 100.0
            if float_compare(line.discount, privilege_discount, precision_digits=2):
                raise ValidationError(self.env._(
                    "%(product)s is discounted by the %(privilege)s privilege, it can't be given another discount.",
                    product=line.full_product_name or line.product_id.display_name,
                    privilege=line.l10n_ph_discount_privilege_id.name,
                ))

    @api.model_create_multi
    def create(self, vals_list):
        # A refund line is discounted and taxed like the line it refunds: it
        # must carry the same privilege and ID holder, or the refunded SC/PWD
        # discount would never be reversed in the privilege reporting. The POS
        # frontend builds refund lines without them (unlike pos.order._refund,
        # which copies the line).
        refunded_lines = self.browse(
            [vals["refunded_orderline_id"] for vals in vals_list if vals.get("refunded_orderline_id")],
        )
        privileged_lines = {line.id: line for line in refunded_lines if line.l10n_ph_discount_privilege_id}
        for vals in vals_list:
            refunded_line = privileged_lines.get(vals.get("refunded_orderline_id"))
            if refunded_line and not vals.get("l10n_ph_discount_privilege_id"):
                vals.update(refunded_line._l10n_ph_prepare_privilege_vals())
        return super().create(vals_list)

    def write(self, vals):
        # Only honored in superuser mode: a user's RPC call can set any context
        # key, and this one hides quantity decreases from the order's log.
        if not (self.env.su and self.env.context.get("l10n_ph_discount_privilege_split")):
            return super().write(vals)
        # Moving quantity to sibling ID holder shares is not an edit of the
        # line: don't let core flag it as one when its quantity decreases.
        unedited_lines = self.filtered(lambda line: not line.is_edited)
        res = super().write(vals)
        if unedited_lines.filtered("is_edited"):
            super(PosOrderLine, unedited_lines).write({"is_edited": False})
        return res

    @api.model
    def _load_pos_data_fields(self, config):
        return [
            *super()._load_pos_data_fields(config),
            "l10n_ph_discount_privilege_id",
            "l10n_ph_original_tax_ids",
            "l10n_ph_original_price_unit",
            "l10n_ph_original_discount",
            "l10n_ph_special_discount_amount",
            *HOLDER_FIELDS,
        ]

    # --- Model-specific hooks for the mixin ---

    def _l10n_ph_is_discount_privilege_eligible(self):
        """
        Whether this line can (still) be split between SC/PWD ID holders:
        real, sold, non-combo products that aren't already privileged.

        Combo lines are excluded for now: splitting a combo child's quantity
        independently of its parent/siblings would desync the combo, and the
        spec's own examples never combine SC/PWD with combo meals. Negative
        lines (global discounts, rewards, ...), tips and service fees aren't
        goods sold to the ID holder.
        """
        self.ensure_one()
        config = self.order_id.config_id
        return (
            not self.l10n_ph_discount_privilege_id
            and self.product_id.type != "combo"
            and not self.combo_parent_id
            and self.qty > 0
            and self.price_unit >= 0
            and self.product_id != config.tip_product_id
            and self.product_id not in (config.available_preset_ids | config.default_preset_id).service_fee_product_id
        )

    def _l10n_ph_privilege_applies(self, privilege):
        """
        Whether ``privilege`` covers this line: its product categories, if
        any, and the taxes its fiscal position exempts (mirrors
        L10nPhDiscountPrivilegeWizard._privilege_applies_to_line). Lines with
        other taxes, e.g. already VAT exempt or zero-rated, are not covered.
        """
        self.ensure_one()
        categories = privilege._l10n_ph_get_applied_category_ids()
        if categories and self.product_id.categ_id not in categories:
            return False
        fiscal_position = privilege.fiscal_position_id
        if fiscal_position:
            taxes = self.l10n_ph_original_tax_ids or self.tax_ids
            return any(fiscal_position.tax_map.get(str(tax.id)) for tax in taxes)
        return True

    def _l10n_ph_get_split_holder_partners(self):
        """ID holders who already had their share of this line split off it."""
        self.ensure_one()
        return self.order_id.lines.filtered(
            lambda line: line.l10n_ph_split_origin_line_id == self,
        ).l10n_ph_holder_partner_id

    def _l10n_ph_skip_discount_amounts(self):
        self.ensure_one()
        return self.product_id.type == "combo"

    def _l10n_ph_prepare_taxed_base_line(self, discount=None):
        """
        Build a fully tax-computed base line for this order line, the way
        _prepare_account_move_line_data_from_base_line does for invoicing.

        :param discount: when set, overrides the line's own discount (e.g.
            0.0 to get the pre-discount/gross tax details) before the tax
            engine computes tax_details on it.
        """
        self.ensure_one()
        company = self.company_id or self.env.company
        base_line = self._prepare_base_lines_for_taxes_computation()[0]
        if discount is not None:
            base_line["discount"] = discount
        self.env["account.tax"]._add_tax_details_in_base_line(base_line, company)
        self.env["account.tax"]._round_base_lines_tax_details([base_line], company)
        return base_line

    def _l10n_ph_get_discount_price_details(self):
        """
        Return the gross (pre-discount) price amounts and the discount
        amounts derived from the current POS order line.

        The gross amounts are recomputed with the tax engine on a base line
        without discount: price_subtotal/price_subtotal_incl are pre-rounded
        amounts that would introduce inaccuracies (and are zero at 100%
        discount).
        """
        self.ensure_one()
        base_line = self._l10n_ph_prepare_taxed_base_line(discount=0.0)
        gross_price_subtotal = base_line["tax_details"]["raw_total_excluded_currency"]
        gross_price_total = base_line["tax_details"]["raw_total_included_currency"]
        return (
            gross_price_subtotal,
            gross_price_subtotal - self.price_subtotal,
            gross_price_total,
            gross_price_total - self.price_subtotal_incl,
        )

    @api.depends(
        "price_unit",
        "qty",
        "discount",
        "tax_ids",
        "price_subtotal",
        "price_subtotal_incl",
        "l10n_ph_discount_privilege_id",
    )
    def _compute_l10n_ph_discount_amounts(self):
        super()._compute_l10n_ph_discount_amounts()

    # --- Splitting engine helpers (called from pos.order) ---

    def _l10n_ph_refresh_amounts(self):
        """
        Refresh price_subtotal(_incl) and extra_tax_data from the current
        price_unit/discount/qty/tax_ids: unlike account.move.line/
        sale.order.line, POS does not auto-compute these from their
        dependencies, and extra_tax_data is normally only ever computed
        client-side, so any server-side mutation must refresh it too or the
        POS frontend's tax display crashes on stale/mismatched data.
        """
        self.ensure_one()
        base_line = self._l10n_ph_prepare_taxed_base_line()
        vals = self._compute_amount_line_all()
        vals["extra_tax_data"] = self.env["account.tax"]._export_base_line_extra_tax_data(base_line)
        self.write(vals)

    def _l10n_ph_set_qty(self, qty, persons_sharing):
        """Resize the regular (unprivileged) share of a split line, now shared
        among ``persons_sharing`` regular persons."""
        self.ensure_one()
        self.write({"qty": qty, "l10n_ph_persons_sharing": persons_sharing})
        self._l10n_ph_refresh_amounts()

    def _l10n_ph_split_prep_lines(self, holder_lines):
        """
        Move this line's quantity already sent to preparation (kitchen) onto
        ``holder_lines``, the new ID holder shares split off it, so that the
        split doesn't show up as cancelled and new items to prepare: the
        sent quantity is given to the holder shares first, so whatever is
        left to send stays on as few lines as possible.
        """
        self.ensure_one()
        prep_lines = self.prep_line_ids.sorted("id")
        sent_qty = sum(prep_line.quantity - prep_line.cancelled for prep_line in prep_lines)
        if sent_qty <= 0:
            return
        digits = self.env["decimal.precision"].precision_get("Product Unit")
        # Copied from an existing preparation line so that the new ones keep
        # its preparation state (e.g. the preparation display stage), instead
        # of showing up as new items to prepare.
        template = prep_lines[-1]
        new_prep_vals = []
        moved_qty = 0.0
        for holder_line in holder_lines:
            qty = min(holder_line.qty, float_round(sent_qty - moved_qty, precision_digits=digits))
            if qty <= 0:
                break
            new_prep_vals += template.copy_data({
                "pos_order_line_id": holder_line.id,
                "quantity": qty,
                "cancelled": 0.0,
            })
            moved_qty += qty
        self.env["pos.prep.line"].create(new_prep_vals)

        # Take the moved quantity off this line's own preparation lines,
        # latest first.
        to_remove = float_round(moved_qty, precision_digits=digits)
        for prep_line in prep_lines[::-1]:
            if to_remove <= 0:
                break
            removed = min(prep_line.quantity - prep_line.cancelled, to_remove)
            prep_line.quantity = float_round(prep_line.quantity - removed, precision_digits=digits)
            to_remove = float_round(to_remove - removed, precision_digits=digits)

    def _l10n_ph_prepare_privilege_vals(self):
        """Privilege and ID holder values to carry onto this line's invoice
        line or refund line (both have the same fields)."""
        self.ensure_one()
        return {
            "l10n_ph_discount_privilege_id": self.l10n_ph_discount_privilege_id.id,
            "l10n_ph_original_tax_ids": [Command.set(self.l10n_ph_original_tax_ids.ids)],
            "l10n_ph_original_price_unit": self.l10n_ph_original_price_unit,
            "l10n_ph_original_discount": self.l10n_ph_original_discount,
            **self._convert_to_write({field: self[field] for field in HOLDER_FIELDS}),
        }

    def _l10n_ph_get_holder_key(self):
        """Identify the ID holder of this line, if any: lines with the same
        key are billed to the same ID holder."""
        self.ensure_one()
        if not self.l10n_ph_discount_privilege_id:
            return None
        return (self.l10n_ph_discount_privilege_id.id, self.l10n_ph_holder_partner_id.id)

    def _l10n_ph_apply_holder_privilege(self, holder_vals, qty):
        """
        Attribute this line to an ID holder: set its quantity, apply the
        holder's discount privilege (VAT-exempt tax swap + statutory
        discount) via the mixin, and refresh the stored subtotals.

        :param holder_vals: the holder's privilege and HOLDER_FIELDS values,
            as prepared by pos.order._l10n_ph_prepare_holders_vals.
        """
        self.ensure_one()
        privilege = self.env["l10n_ph.discount.privilege"].browse(holder_vals["l10n_ph_discount_privilege_id"])
        self.write({
            **holder_vals,
            "qty": qty,
            # A line entering this method is never already privileged (the
            # engine copies shares before privileging any of them), so the
            # current discount is always the pre-privilege one worth
            # preserving; mirrors L10nPhDiscountPrivilegeWizard.action_confirm.
            # It is replaced, never combined: no double discounting.
            "l10n_ph_original_discount": self.discount,
            "discount": privilege.discount_amount * 100.0,
            # The POS reprices "original" lines from the pricelist (e.g. when
            # the customer changes), which would undo the VAT removal below.
            "price_type": "manual",
        })
        # The POS prices lines with the taxes' own "Included in Price" (no
        # document-level tax mode, unlike invoices).
        new_price_unit, original_price_unit = self._adjust_price_unit_from_privilege(
            self.price_unit, self.tax_ids, None,
        )
        new_taxes, original_taxes = self._adjust_taxes_from_privilege(self.tax_ids)
        self.write(
            {
                "price_unit": new_price_unit,
                "l10n_ph_original_price_unit": original_price_unit,
                "tax_ids": [Command.set(new_taxes.ids)],
                "l10n_ph_original_tax_ids": [Command.set(original_taxes.ids)] if original_taxes else False,
            },
        )
        self._l10n_ph_refresh_amounts()

    def _l10n_ph_remove_holder_privilege(self):
        """
        Undo the split of this ID holder share: give its quantity back to the
        regular share it was split off, with its ID holder as one more person
        sharing it, or turn it back into a regular line of its own when there
        is no such share anymore.
        """
        self.ensure_one()
        origin = self.l10n_ph_split_origin_line_id
        if (
            origin
            and origin.order_id == self.order_id
            and not origin.l10n_ph_discount_privilege_id
            and origin.product_id == self.product_id
        ):
            # The quantity sent to preparation goes back with it.
            self.prep_line_ids.pos_order_line_id = origin
            origin._l10n_ph_set_qty(
                origin.qty + self.qty,
                origin.l10n_ph_persons_sharing + 1 if origin.l10n_ph_persons_sharing else 0,
            )
            self.unlink()
            return origin
        self.write({
            "l10n_ph_discount_privilege_id": False,
            **dict.fromkeys(HOLDER_FIELDS, False),
            "price_unit": self.l10n_ph_original_price_unit or self.price_unit,
            "l10n_ph_original_price_unit": 0.0,
            "tax_ids": [Command.set((self.l10n_ph_original_tax_ids or self.tax_ids).ids)],
            "l10n_ph_original_tax_ids": [Command.clear()],
            "discount": self.l10n_ph_original_discount,
            "l10n_ph_original_discount": 0.0,
            "l10n_ph_split_origin_line_id": False,
            # This share was one person's.
            "l10n_ph_persons_sharing": 1,
        })
        self._l10n_ph_refresh_amounts()
        return self
