# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.exceptions import UserError
from odoo.fields import Command


class PosOrder(models.Model):
    _inherit = "pos.order"

    l10n_ph_discount_privilege_holder_ids = fields.One2many(
        "l10n_ph.pos.discount.privilege.holder",
        "order_id",
        string="SC/PWD ID Holders",
    )

    def l10n_ph_apply_discount_privileges(self, holders_vals, num_persons_sharing, target_line_uuid=None):
        """
        RPC entry point called from the POS frontend's Discount Privileges
        dialog. Delegates to _l10n_ph_apply_discount_privileges, then returns
        the affected records in the same shape as read_pos_data(), so the
        frontend can merge them into its local store the way it already does
        for any other server-driven mutation (see PosData.callRelated).
        """
        self.ensure_one()
        target_line = (
            self.lines.filtered(lambda line: line.uuid == target_line_uuid)
            if target_line_uuid
            else None
        )
        holders = self._l10n_ph_apply_discount_privileges(holders_vals, num_persons_sharing, target_line)
        return {
            "pos.order": self._load_pos_data_read(self, self.config_id),
            "pos.order.line": self.env["pos.order.line"]._load_pos_data_read(self.lines, self.config_id),
            "l10n_ph.pos.discount.privilege.holder": self.env[
                "l10n_ph.pos.discount.privilege.holder"
            ]._load_pos_data_read(holders, self.config_id),
        }

    def _l10n_ph_get_discount_privilege_lines(self):
        """
        Product lines eligible for a (further) SC/PWD discount privilege
        split: real, non-combo lines that aren't already privileged.

        Combo lines are excluded for now: splitting a combo child's quantity
        independently of its parent/siblings would desync the combo, and the
        spec's own examples never combine SC/PWD with combo meals.
        """
        self.ensure_one()
        return self.lines.filtered(
            lambda line: not line.l10n_ph_discount_privilege_id
            and line.product_id.type != "combo"
            and not line.combo_parent_id,
        )

    def _l10n_ph_apply_discount_privileges(self, holders_vals, num_persons_sharing, target_line=None):
        """
        Split the order (or a single ``target_line``) between a "regular"
        share and one share per SC/PWD ID holder, applying each holder's
        discount privilege (VAT-exempt tax swap + statutory discount) via
        l10n_ph.discount.privilege.line.mixin on the resulting lines.

        :param holders_vals: list of create vals for
            l10n_ph.pos.discount.privilege.holder (each must set privilege_id);
            one entry per ID presented.
        :param num_persons_sharing: total headcount sharing the targeted
            quantity (must be >= the number of ID holders); the remainder is
            the "regular" (undiscounted) share.
        :param target_line: when set, restrict the split to this single line
            — spec: "one product selected", the item is exclusively for the
            named ID holder(s) and the rest of the order is untouched. When
            unset, split every currently non-privileged, non-combo product
            line — spec: "no product selected", the whole shared order is
            pro-rated by headcount.
        :return: the created l10n_ph.pos.discount.privilege.holder records.
        """
        self.ensure_one()
        if not holders_vals:
            raise UserError(self.env._("Select at least one discount privilege to apply."))
        if num_persons_sharing < len(holders_vals):
            raise UserError(
                self.env._(
                    "The number of persons sharing must be at least the number of IDs presented.",
                ),
            )
        if target_line:
            if target_line.order_id != self:
                raise UserError(self.env._("The selected line does not belong to this order."))
            if target_line.l10n_ph_discount_privilege_id:
                raise UserError(self.env._("This line already has a discount privilege applied."))
            if target_line.product_id.type == "combo" or target_line.combo_parent_id:
                raise UserError(self.env._("Discount privileges cannot be applied to combo lines."))
            lines = target_line
        else:
            lines = self._l10n_ph_get_discount_privilege_lines()
            if not lines:
                raise UserError(self.env._("There are no more lines to apply a discount privilege on."))

        holders = self.env["l10n_ph.pos.discount.privilege.holder"].create(
            [{**vals, "order_id": self.id} for vals in holders_vals],
        )
        num_regular = num_persons_sharing - len(holders)

        for line in lines:
            self._l10n_ph_split_line_for_holders(line, holders, num_regular, num_persons_sharing)

        return holders

    def _l10n_ph_split_line_for_holders(self, line, holders, num_regular, num_persons_sharing):
        """
        Split a single ``line`` into a (possibly reduced) regular share and
        one sibling line per holder in ``holders``, applying each holder's
        privilege via the mixin.
        """
        self.ensure_one()
        per_person_qty = line.qty / num_persons_sharing

        if num_regular > 0:
            remaining_holders = holders
            line._l10n_ph_set_qty(per_person_qty * num_regular)
        else:
            # Nothing regular is left on this line: reuse it for the first
            # holder instead of shrinking it to zero and orphaning it.
            first_holder, remaining_holders = holders[0], holders[1:]
            line._l10n_ph_apply_holder_privilege(first_holder, per_person_qty)

        for holder in remaining_holders:
            new_line = line.copy({"order_id": self.id, "qty": per_person_qty})
            new_line._l10n_ph_apply_holder_privilege(holder, per_person_qty)

    # --- Invoice propagation ---

    def _prepare_account_move_line_data_from_base_line(self, base_lines):
        """
        Extend the base per-product invoice lines with the privilege fields
        (mirrors SaleOrderLine._prepare_invoice_line) and group them into one
        "line_section" per ID holder plus one for the regular share, so the
        generated customer invoice matches the BIR-required layout: each
        ID holder's name/ID clearly attached to the products billed to them.
        """
        self.ensure_one()
        if not self.l10n_ph_discount_privilege_holder_ids:
            return super()._prepare_account_move_line_data_from_base_line(base_lines)

        def holder_of(base_line):
            return base_line["record"].l10n_ph_discount_privilege_holder_id

        ordered_base_lines = sorted(base_lines, key=lambda bl: holder_of(bl).id)
        to_create = super()._prepare_account_move_line_data_from_base_line(ordered_base_lines)

        result = []
        current_group_id = None
        for entry in to_create:
            line = entry["metadata"].get("line")
            if line is not None:
                holder = line.l10n_ph_discount_privilege_holder_id
                if holder.id != current_group_id:
                    result.append(self._l10n_ph_prepare_section_line(holder))
                    current_group_id = holder.id
                if line.l10n_ph_discount_privilege_id:
                    entry["account.move.line"].update(
                        {
                            "l10n_ph_discount_privilege_id": line.l10n_ph_discount_privilege_id.id,
                            "l10n_ph_original_tax_ids": [
                                Command.set(line.l10n_ph_original_tax_ids.ids),
                            ],
                            "l10n_ph_original_price_unit": line.l10n_ph_original_price_unit,
                            "l10n_ph_original_discount": line.l10n_ph_original_discount,
                        },
                    )
            result.append(entry)
        return result

    def _l10n_ph_prepare_section_line(self, holder):
        if holder:
            name = self.env._(
                "ID HOLDER %(name)s — ID Type: %(privilege)s — ID#: %(id_number)s",
                name=holder.name,
                privilege=holder.privilege_id.name,
                id_number=holder.id_number,
            )
        else:
            name = self.env._("Regular orders")
        return {
            "account.move.line": {"display_type": "line_section", "name": name},
            "metadata": {},
        }
