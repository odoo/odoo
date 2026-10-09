// Part of Odoo. See LICENSE file for full copyright and licensing details.

import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { ConnectionLostError } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

// Patched in: the order summary has no other extension point for extra details,
// nor for numpad input on the selected line.
patch(OrderSummary.prototype, {
    async updateSelectedOrderline({ key }) {
        if (!this.currentOrder.getSelectedOrderline()?.l10n_ph_discount_privilege_id) {
            return super.updateSelectedOrderline(...arguments);
        }
        // A privileged share's quantity, discount and price are set by the
        // split: it can only be given back to the regular share, e.g. to undo
        // a mistaken split.
        this.numberBuffer.reset();
        if (key === "Backspace") {
            await this.l10nPhRemoveDiscountPrivilege();
        } else {
            this.dialog.add(AlertDialog, {
                title: _t("Cannot modify a discount privilege share"),
                body: _t(
                    "Its quantity is shared among the persons of the order and its discount is the privilege's. Press Backspace to undo the discount privilege."
                ),
            });
        }
    },
    async l10nPhRemoveDiscountPrivilege() {
        // A repeated Backspace would try to remove it again.
        if (this.l10nPhRemovingPrivilege) {
            return;
        }
        const order = this.currentOrder;
        const line = order.getSelectedOrderline();
        this.l10nPhRemovingPrivilege = true;
        try {
            await this.pos.l10nPhRemoveDiscountPrivilege(order, line);
        } catch (error) {
            this.dialog.add(AlertDialog, {
                title: _t("Could not remove the discount privilege"),
                body:
                    error instanceof ConnectionLostError
                        ? _t(
                              "This requires an internet connection. Please try again once you're back online."
                          )
                        : error?.data?.message || error?.message || String(error),
            });
        } finally {
            this.l10nPhRemovingPrivilege = false;
        }
    },
    l10nPhGetDiscountBreakdown() {
        const totals = new Map();
        for (const line of this.currentOrder.lines) {
            const privilege = line.l10n_ph_discount_privilege_id;
            if (!privilege) {
                continue;
            }
            const row = totals.get(privilege.id) || { privilege, amount: 0 };
            row.amount += line.l10n_ph_special_discount_amount || 0;
            totals.set(privilege.id, row);
        }
        return [...totals.values()];
    },
});
