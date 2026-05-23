/** @odoo-module */

import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { NoteButton } from "@point_of_sale/app/screens/product_screen/control_buttons/orderline_note_button/orderline_note_button";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

function _isMinimalCashier(pos) {
    return pos.getCashier()._role === "minimal";
}

// 1. PosOrderline: expose isKitchenSent() and inject the CSS class via getDisplayClasses()
patch(PosOrderline.prototype, {
    isKitchenSent() {
        return (this.uiState?.savedQuantity ?? 0) > 0;
    },
    getDisplayClasses() {
        return {
            ...super.getDisplayClasses(),
            "kitchen-sent-locked": this.isKitchenSent(),
        };
    },
});

// 2. OrderSummary: block all numpad operations (qty / price / discount / delete)
//    on kitchen-sent lines when the current cashier has minimal rights.
patch(OrderSummary.prototype, {
    _setValue(val) {
        const selectedLine = this.currentOrder?.getSelectedOrderline();
        if (selectedLine?.isKitchenSent() && _isMinimalCashier(this.pos)) {
            this.dialog.add(AlertDialog, {
                title: _t("Manager Approval Required"),
                body: _t(
                    "This line has already been sent to the kitchen. A manager must approve any changes."
                ),
            });
            this.numberBuffer.reset();
            return;
        }
        return super._setValue(val);
    },

    // Block long-press product re-configuration on kitchen-sent lines for minimal cashiers.
    async onOrderlineLongPress(ev, orderline) {
        const line = orderline.combo_parent_id ?? orderline;
        if (line.isKitchenSent() && _isMinimalCashier(this.pos)) {
            this.dialog.add(AlertDialog, {
                title: _t("Manager Approval Required"),
                body: _t(
                    "This line has already been sent to the kitchen. A manager must approve any changes."
                ),
            });
            return false;
        }
        return super.onOrderlineLongPress(ev, orderline);
    },
});

// 3. NoteButton: block note edits on kitchen-sent lines for minimal cashiers.
patch(NoteButton.prototype, {
    async onClick() {
        const selectedLine = this.pos.getOrder()?.getSelectedOrderline();
        if (selectedLine?.isKitchenSent() && _isMinimalCashier(this.pos)) {
            this.dialog.add(AlertDialog, {
                title: _t("Manager Approval Required"),
                body: _t(
                    "This line has already been sent to the kitchen. A manager must approve any changes."
                ),
            });
            return { confirmed: false };
        }
        return super.onClick();
    },
});
