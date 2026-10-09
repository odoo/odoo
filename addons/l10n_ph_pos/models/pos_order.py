# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tools import float_compare, float_round

from odoo.addons.l10n_ph_invoice.models.l10n_ph_discount_privilege import (
    PARTNER_IDENTIFIER_KEYS,
)


class PosOrder(models.Model):
    _inherit = "pos.order"

    def message_post(self, **kwargs):
        # Moving quantity from a line to its sibling ID holder shares is not
        # an edit of the order: drop core's "Ordered quantity" log for it, the
        # split posts its own summary instead (see _l10n_ph_split_line_for_holders).
        # Only honored in superuser mode: a user's RPC call can set any context
        # key, and this one would hide the order's audit trail.
        if self.env.su and self.env.context.get("l10n_ph_discount_privilege_split"):
            return self.env["mail.message"]
        return super().message_post(**kwargs)

    def l10n_ph_apply_discount_privileges(self, holders_vals, num_persons_sharing, target_line_uuid=None):
        """
        RPC entry point called from the POS frontend's Discount Privileges
        dialog. Delegates to _l10n_ph_apply_discount_privileges, then returns
        the order's records (see _l10n_ph_read_pos_data).
        """
        self.ensure_one()
        target_line = None
        if target_line_uuid:
            target_line = self.lines.filtered(lambda line: line.uuid == target_line_uuid)
            # Never fall back on the whole order when the selected line can't
            # be found: that would privilege far more than the cashier asked.
            if not target_line:
                raise UserError(self.env._("The selected line does not belong to this order."))
        self._l10n_ph_apply_discount_privileges(holders_vals, num_persons_sharing, target_line)
        return self._l10n_ph_read_pos_data()

    def l10n_ph_remove_discount_privilege(self, line_uuid):
        """
        RPC entry point called from the POS frontend when an ID holder share
        is removed (see pos.order.line._l10n_ph_remove_holder_privilege).
        Returns the order's records like l10n_ph_apply_discount_privileges:
        the share is no longer among them when it was merged back.
        """
        self.ensure_one()
        if self.state != "draft":
            raise UserError(self.env._("Discount privileges can only be removed from unpaid orders."))
        line = self.lines.filtered(lambda line: line.uuid == line_uuid and line.l10n_ph_discount_privilege_id)
        if not line:
            raise UserError(self.env._("The selected line has no discount privilege on this order."))
        body = self.env._(
            "Discount privilege of %(holder)s removed from %(product)s.",
            holder=line.l10n_ph_holder_name,
            product=line.full_product_name or line.product_id.display_name,
        )
        # sudo: see _l10n_ph_split_line_for_holders, giving the quantity back
        # to the regular share is not an edit of the order either.
        line.sudo().with_context(l10n_ph_discount_privilege_split=True)._l10n_ph_remove_holder_privilege()
        self._compute_prices()
        self.message_post(body=body)
        return self._l10n_ph_read_pos_data()

    def _l10n_ph_read_pos_data(self):
        """The order's records, in the same shape as read_pos_data(), so the
        frontend can merge them into its local store (see PosData.callRelated)."""
        self.ensure_one()
        return {
            "pos.order": self._load_pos_data_read(self, self.config_id),
            "pos.order.line": self.env["pos.order.line"]._load_pos_data_read(self.lines, self.config_id),
            "pos.prep.line": self.env["pos.prep.line"]._load_pos_data_read(
                self.lines.prep_line_ids, self.config_id,
            ),
            "res.partner": self.env["res.partner"]._load_pos_data_read(
                self.lines.l10n_ph_holder_partner_id, self.config_id,
            ),
            "product.attribute.custom.value": self.env["product.attribute.custom.value"]._load_pos_data_read(
                self.lines.custom_attribute_value_ids, self.config_id,
            ),
        }

    def _l10n_ph_get_discount_privilege_lines(self):
        """
        Product lines eligible for a (further) SC/PWD discount privilege
        split (see pos.order.line._l10n_ph_is_discount_privilege_eligible).
        """
        self.ensure_one()
        return self.lines.filtered(lambda line: line._l10n_ph_is_discount_privilege_eligible())

    def _l10n_ph_apply_discount_privileges(self, holders_vals, num_persons_sharing, target_line=None):
        """
        Split the order (or a single ``target_line``) between a "regular"
        share and one share per SC/PWD ID holder, applying each holder's
        discount privilege (VAT-exempt tax swap + statutory discount) via
        l10n_ph.discount.privilege.line.mixin on the resulting lines.

        :param holders_vals: one dict per ID presented, with the keys
            ``privilege_id``, ``partner_id`` (the ID holder's contact, holding
            their ID number among its additional identifiers) and, when the ID
            holder is not present, ``representative_name`` and
            ``representative_id``.
        :param num_persons_sharing: total headcount sharing the targeted
            quantity (must be >= the number of ID holders); the remainder is
            the "regular" (undiscounted) share. A regular share left by an
            earlier split keeps its own headcount instead (see
            pos.order.line.l10n_ph_persons_sharing).
        :param target_line: when set, restrict the split to this single line
            (spec: "one product selected"), the item is exclusively for the
            named ID holder(s) and the rest of the order is untouched. When
            unset, split every currently non-privileged, non-combo product
            line (spec: "no product selected"), the whole shared order is
            pro-rated by headcount.
        """
        self.ensure_one()
        if self.state != "draft":
            raise UserError(self.env._("Discount privileges can only be applied to unpaid orders."))
        if not holders_vals:
            raise UserError(self.env._("Select at least one discount privilege to apply."))
        if isinstance(num_persons_sharing, bool) or not isinstance(num_persons_sharing, int):
            raise UserError(self.env._("The number of persons sharing must be a whole number."))
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
            if not target_line._l10n_ph_is_discount_privilege_eligible():
                raise UserError(self.env._("Discount privileges cannot be applied to this line."))
            lines = target_line
        else:
            lines = self._l10n_ph_get_discount_privilege_lines()
            if not lines:
                raise UserError(self.env._("There are no more lines to apply a discount privilege on."))

        holders = self._l10n_ph_prepare_holders_vals(holders_vals)
        privileges = self.env["l10n_ph.discount.privilege"].browse(
            {holder["l10n_ph_discount_privilege_id"] for holder in holders},
        )
        holders_per_line = {}
        for line in lines:
            product = line.full_product_name or line.product_id.display_name
            split_partners = line._l10n_ph_get_split_holder_partners()
            line_holders = []
            for holder in holders:
                privilege = privileges.browse(holder["l10n_ph_discount_privilege_id"])
                # An ID holder already has their share of a regular share left
                # by an earlier split: they're not among its persons anymore.
                if holder["l10n_ph_holder_partner_id"] in split_partners.ids:
                    if target_line:
                        raise UserError(self.env._(
                            "%(holder)s already has their share of %(product)s.",
                            holder=holder["l10n_ph_holder_name"],
                            product=product,
                        ))
                # Not covered by the privilege (product category, taxes): the
                # ID holder's share stays among the regular ones.
                elif not line._l10n_ph_privilege_applies(privilege):
                    if target_line:
                        raise UserError(self.env._(
                            "The %(privilege)s privilege does not apply to %(product)s: check the product "
                            "categories set on the privilege and the taxes of the product.",
                            privilege=privilege.name,
                            product=product,
                        ))
                else:
                    line_holders.append(holder)
            if not line_holders:
                continue
            num_line_persons = line.l10n_ph_persons_sharing or num_persons_sharing
            if num_line_persons < len(line_holders):
                raise UserError(
                    self.env._(
                        "Only %(count)s regular persons are left sharing %(product)s.",
                        count=num_line_persons,
                        product=product,
                    ),
                )
            holders_per_line[line] = (line_holders, num_line_persons)
        if not holders_per_line:
            raise UserError(self.env._(
                "The selected discount privileges do not apply to any line of this order. Please check the "
                "product categories set on the privileges and the taxes of the products.",
            ))

        for line, (line_holders, num_line_persons) in holders_per_line.items():
            self._l10n_ph_split_line_for_holders(line, line_holders, num_line_persons)
        # The split lines are discounted and VAT exempt: keep the order's
        # stored totals in line with them.
        self._compute_prices()

        applied_partner_ids = {
            holder["l10n_ph_holder_partner_id"]
            for line_holders, _num_line_persons in holders_per_line.values()
            for holder in line_holders
        }
        holder_descriptions = [
            f"{holder['l10n_ph_holder_name']} "
            f"({privileges.browse(holder['l10n_ph_discount_privilege_id']).l10n_ph_id_type_label}: "
            f"{holder['l10n_ph_holder_id_number']})"
            for holder in holders
            if holder["l10n_ph_holder_partner_id"] in applied_partner_ids
        ]
        if target_line:
            body = self.env._(
                "Discount privileges applied on %(product)s for %(holders)s.",
                product=target_line.full_product_name or target_line.product_id.display_name,
                holders=holder_descriptions,
            )
        else:
            body = self.env._(
                "Discount privileges applied on the order shared among %(count)s persons for %(holders)s.",
                count=num_persons_sharing,
                holders=holder_descriptions,
            )
        self.message_post(body=body)

    def _l10n_ph_prepare_holders_vals(self, holders_vals):
        """
        Validate the ID holders sent by the POS and convert each of them into
        the pos.order.line values attributing a share to them (see
        _l10n_ph_apply_discount_privileges for the expected keys).
        """
        self.ensure_one()
        Privilege = self.env["l10n_ph.discount.privilege"]
        privileges = Privilege.search([
            ("id", "in", [vals.get("privilege_id") for vals in holders_vals]),
            *Privilege._check_company_domain(self.company_id),
        ])
        partners = self.env["res.partner"].browse(
            {vals["partner_id"] for vals in holders_vals if vals.get("partner_id")},
        ).exists()
        holders = []
        for vals in holders_vals:
            privilege = privileges.filtered(lambda privilege: privilege.id == vals.get("privilege_id"))
            if not privilege:
                raise UserError(self.env._("Select a discount privilege of this company for every ID holder."))
            partner = partners.filtered(lambda partner: partner.id == vals.get("partner_id"))
            if not partner:
                raise UserError(self.env._("Select the contact of every ID holder."))
            # Statutory privileges require the ID holder's ID, from their contact.
            id_number = privilege._l10n_ph_get_partner_id_number(partner)
            if privilege.discount_type in PARTNER_IDENTIFIER_KEYS and not id_number:
                raise UserError(self.env._(
                    "%(partner)s has no %(id_type)s: add it on their contact first.",
                    partner=partner.name,
                    id_type=privilege.l10n_ph_id_type_label,
                ))
            representative_name, representative_id = (
                (vals.get(key) or "").strip() for key in ("representative_name", "representative_id")
            )
            if bool(representative_name) != bool(representative_id):
                raise UserError(self.env._(
                    "The representative's name and ID are required when the ID holder %s is not present.",
                    partner.name,
                ))
            holders.append({
                "l10n_ph_discount_privilege_id": privilege.id,
                "l10n_ph_holder_partner_id": partner.id,
                "l10n_ph_holder_name": partner.name,
                "l10n_ph_holder_id_number": id_number or False,
                "l10n_ph_holder_representative_name": representative_name or False,
                "l10n_ph_holder_representative_id": representative_id or False,
            })
        self._l10n_ph_check_one_privilege_per_holder(holders)
        return holders

    def _l10n_ph_check_one_privilege_per_holder(self, holders):
        """
        A person can't claim more than one privilege, or present more than
        one ID, on the same order: SC/PWD discounts can't be combined (no
        double discounting). An ID holder already on the order may only be
        given further shares with the same privilege and ID.

        A person is identified by their contact.
        """
        def person_key(holder):
            return holder["l10n_ph_holder_partner_id"]

        def id_key(holder):
            return (holder["l10n_ph_discount_privilege_id"], holder["l10n_ph_holder_id_number"])

        existing_holders = [
            {
                "l10n_ph_discount_privilege_id": line.l10n_ph_discount_privilege_id.id,
                "l10n_ph_holder_partner_id": line.l10n_ph_holder_partner_id.id,
                "l10n_ph_holder_id_number": line.l10n_ph_holder_id_number,
            }
            for line in self.lines.filtered("l10n_ph_discount_privilege_id")
        ]
        ids_per_person = {person_key(holder): id_key(holder) for holder in existing_holders}
        persons_per_id = {id_key(holder): person_key(holder) for holder in existing_holders}
        seen_persons = set()
        for holder in holders:
            person, holder_id = person_key(holder), id_key(holder)
            if person in seen_persons:
                raise UserError(self.env._(
                    "%s can only present one ID: discount privileges can't be combined.",
                    holder["l10n_ph_holder_name"],
                ))
            if ids_per_person.get(person, holder_id) != holder_id:
                raise UserError(self.env._(
                    "%s already claims a discount privilege on this order with another ID: "
                    "discount privileges can't be combined.",
                    holder["l10n_ph_holder_name"],
                ))
            if holder_id[1] and persons_per_id.get(holder_id, person) != person:
                raise UserError(self.env._(
                    "The ID %s was already presented by someone else on this order.",
                    holder["l10n_ph_holder_id_number"],
                ))
            seen_persons.add(person)
            ids_per_person[person] = holder_id
            persons_per_id[holder_id] = person

    def _l10n_ph_split_line_for_holders(self, line, holders, num_persons_sharing):
        """
        Split a single ``line`` shared among ``num_persons_sharing`` persons
        into a (possibly reduced) regular share and one sibling line per
        holder in ``holders``, applying each holder's privilege via the mixin.
        """
        self.ensure_one()
        digits = self.env["decimal.precision"].precision_get("Product Unit")
        num_regular = num_persons_sharing - len(holders)
        original_qty = line.qty
        per_person_qty = float_round(original_qty / num_persons_sharing, precision_digits=digits)
        regular_qty = float_round(original_qty * num_regular / num_persons_sharing, precision_digits=digits)
        holder_qtys = [per_person_qty] * len(holders)
        # Each share is rounded to the quantity precision on its own: the
        # last holder share absorbs the residual so that the shares always
        # sum back to the original quantity (e.g. 1 unit for 3 holders gives
        # 0.33 + 0.33 + 0.34, not 0.99).
        holder_qtys[-1] = float_round(
            original_qty - regular_qty - per_person_qty * (len(holders) - 1),
            precision_digits=digits,
        )
        shares = holder_qtys + ([regular_qty] if num_regular > 0 else [])
        if any(float_compare(qty, 0.0, precision_digits=digits) <= 0 for qty in shares):
            raise UserError(self.env._(
                "The quantity of %(product)s is too small to be shared among %(count)s persons.",
                product=line.full_product_name or line.product_id.display_name,
                count=num_persons_sharing,
            ))

        # Nothing regular left on this line: reuse it for the first holder
        # instead of shrinking it to zero and orphaning it.
        reuse_line = num_regular <= 0
        # Copy the line while it is still unprivileged, so every holder share
        # starts from the pre-privilege price, taxes and discount.
        copy_vals = line.copy_data({
            "order_id": self.id,
            "l10n_ph_persons_sharing": 0,
            "l10n_ph_split_origin_line_id": line.id,
            # Not copied with the line (one2many): the shares are the same
            # product, customized the same way.
            "custom_attribute_value_ids": [
                Command.create(vals)
                for vals in line.custom_attribute_value_ids.copy_data({"pos_order_line_id": False})
            ],
        })[0]
        copies = self.env["pos.order.line"].create([
            {**copy_vals, "qty": qty} for qty in holder_qtys[1 if reuse_line else 0:]
        ])
        line._l10n_ph_split_prep_lines(copies)

        # Shrinking the original line moves quantity to its siblings, it is
        # not an edit of the order (see message_post and PosOrderLine.write).
        # sudo: those overrides only trust their context key in superuser mode;
        # the values written here are computed above, on a line of this draft
        # order that _l10n_ph_apply_discount_privileges already validated.
        split_line = line.sudo().with_context(l10n_ph_discount_privilege_split=True)
        if reuse_line:
            split_line._l10n_ph_apply_holder_privilege(holders[0], holder_qtys[0])
        else:
            split_line._l10n_ph_set_qty(regular_qty, num_regular)
        first_copy_share = 1 if reuse_line else 0
        holder_shares = zip(copies, holders[first_copy_share:], holder_qtys[first_copy_share:], strict=True)
        for holder_line, holder, qty in holder_shares:
            holder_line._l10n_ph_apply_holder_privilege(holder, qty)

    # --- Invoice propagation ---

    def _prepare_account_move_line_data(self, aggregate=True):
        """
        Group the invoice lines into one "line_section" per ID holder plus
        one for the regular share, both on the customer invoice of an order
        and on the session's global invoice, so each ID holder's name/ID is
        clearly attached to the products billed to them (BIR layout).
        """
        entries = super()._prepare_account_move_line_data(aggregate)
        return self._l10n_ph_group_move_line_entries_by_holder(entries)

    def _prepare_account_move_line_data_from_base_line(self, base_lines):
        """
        Carry the privilege of privileged lines onto their invoice line
        (mirrors SaleOrderLine._prepare_invoice_line).
        """
        entries = super()._prepare_account_move_line_data_from_base_line(base_lines)
        for entry in entries:
            line = entry["metadata"].get("line")
            if (
                line
                and line.l10n_ph_discount_privilege_id
                and entry["account.move.line"].get("display_type") == "product"
            ):
                entry["account.move.line"].update(line._l10n_ph_prepare_privilege_vals())
        return entries

    def _aggregate_base_line_and_prepare_account_move_line_data(self, base_lines):
        """
        On the session's global invoice, never merge ID holder shares with
        the regular sales: each keeps its own invoice line, discount and
        privilege, so the SC/PWD discount stays reportable per ID holder.
        """
        holder_base_lines = [bl for bl in base_lines if bl["record"].l10n_ph_discount_privilege_id]
        if not holder_base_lines:
            return super()._aggregate_base_line_and_prepare_account_move_line_data(base_lines)

        regular_base_lines = [bl for bl in base_lines if not bl["record"].l10n_ph_discount_privilege_id]
        entries = (
            super()._aggregate_base_line_and_prepare_account_move_line_data(regular_base_lines)
            if regular_base_lines
            else []
        )
        # Zero-priced lines are already added line by line by the caller.
        holder_base_lines = [bl for bl in holder_base_lines if not bl["currency_id"].is_zero(bl["price_unit"])]
        self.env["account.tax"]._fix_base_lines_tax_details_on_manual_tax_amounts(
            holder_base_lines, self.company_id,
        )
        base_lines_per_order = {}
        for base_line in holder_base_lines:
            base_lines_per_order.setdefault(base_line["record"].order_id, []).append(base_line)
        for order, order_base_lines in base_lines_per_order.items():
            # Keep the product lines only: the order's notes have no place on
            # the session's global invoice.
            entries += [
                entry
                for entry in order._prepare_account_move_line_data_from_base_line(order_base_lines)
                if entry["metadata"].get("line")
            ]
        return entries

    def _l10n_ph_group_move_line_entries_by_holder(self, entries):
        """
        Reorder ``entries`` (as returned by _prepare_account_move_line_data)
        into a regular group followed by one group per ID holder, in order of
        appearance, each one headed by its own "line_section". Notes stay
        with the line they follow, except the order's general customer note,
        moved ahead of all sections: it belongs to none of them. Entries are
        returned unchanged when no line has an ID holder.
        """
        # Always added last, after the note of the last line if any (see
        # _prepare_account_move_line_data_from_base_line).
        general_note_entries = []
        if (
            len(self) == 1
            and self.general_customer_note
            and entries
            and not entries[-1]["metadata"]
            and entries[-1]["account.move.line"].get("display_type") == "line_note"
            and entries[-1]["account.move.line"].get("name") == self.general_customer_note
        ):
            entries, general_note_entries = entries[:-1], entries[-1:]

        keyed_entries = []
        holder_lines = {}  # holder key -> first line of that ID holder
        key = None
        for entry in entries:
            line = entry["metadata"].get("line")
            if line:
                key = line._l10n_ph_get_holder_key()
                holder_lines.setdefault(key, line)
            elif "base_line" in entry["metadata"]:
                # Aggregated regular sales of the session's global invoice.
                key = None
            keyed_entries.append((key, entry))
        if not any(key for key, _entry in keyed_entries):
            return entries + general_note_entries

        sequence = {key: index for index, key in enumerate(dict.fromkeys([None, *holder_lines]))}
        result = general_note_entries
        current_key = False  # matches no holder key, not even the regular one (None)
        for key, entry in sorted(keyed_entries, key=lambda item: sequence[item[0]]):
            if key != current_key:
                result.append(self._l10n_ph_prepare_section_line(key and holder_lines[key]))
                current_key = key
            result.append(entry)
        return result

    def _l10n_ph_prepare_section_line(self, holder_line):
        """Section heading the invoice lines of ``holder_line``'s ID holder,
        or the regular ones when it is unset."""
        if holder_line:
            name = self.env._(
                "ID HOLDER %(name)s - ID Type: %(id_type)s - ID#: %(id_number)s",
                name=holder_line.l10n_ph_holder_name,
                id_type=holder_line.l10n_ph_discount_privilege_id.l10n_ph_id_type_label,
                id_number=holder_line.l10n_ph_holder_id_number,
            )
        else:
            name = self.env._("Regular Orders")
        return {
            "account.move.line": {"display_type": "line_section", "name": name},
            "metadata": {},
        }
