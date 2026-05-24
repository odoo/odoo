/** @odoo-module */

import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { NoteButton, InternalNoteButton } from "@point_of_sale/app/screens/product_screen/control_buttons/orderline_note_button/orderline_note_button";
import { ManagerOverrideDialog } from "@pos_kitchen_lock/js/manager_override_dialog";
import { patch } from "@web/core/utils/patch";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { _t } from "@web/core/l10n/translation";

function _isMinimalCashier(pos) {
    return pos.getCashier()._role === "minimal";
}

/**
 * Prompt the manager selection dialog, switch the session cashier on success,
 * and show a sticky "Lock Session" notification.
 * Returns true if a manager authenticated, false if the user cancelled.
 */
async function _applyManagerOverride(component) {
    const manager = await makeAwaitable(component.dialog, ManagerOverrideDialog, {});
    if (!manager) {
        return false;
    }
    component.pos.setCashier(manager);
    component.env.services.notification.add(
        _t("Manager session active. Lock the session when finished."),
        {
            type: "info",
            sticky: true,
            title: _t("Manager Override"),
            buttons: [
                {
                    name: _t("Lock Session"),
                    primary: true,
                    onClick: () => component.pos.showLoginScreen(),
                },
            ],
        }
    );
    return true;
}

// ── 1. PosOrderline ────────────────────────────────────────────────────────────
// Expose isKitchenSent() and inject the CSS class through getDisplayClasses().
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

// ── 2. OrderSummary ────────────────────────────────────────────────────────────
// Block numpad changes (qty / price / discount / delete) and long-press
// re-configuration on kitchen-sent lines for minimal cashiers.
patch(OrderSummary.prototype, {
    async _setValue(val) {
        const selectedLine = this.currentOrder?.getSelectedOrderline();
        if (selectedLine?.isKitchenSent() && _isMinimalCashier(this.pos)) {
            this.numberBuffer.reset();
            const ok = await _applyManagerOverride(this);
            if (ok) {
                super._setValue(val);
            }
            return;
        }
        return super._setValue(val);
    },

    async onOrderlineLongPress(ev, orderline) {
        const line = orderline.combo_parent_id ?? orderline;
        if (line.isKitchenSent() && _isMinimalCashier(this.pos)) {
            const ok = await _applyManagerOverride(this);
            if (!ok) {
                return false;
            }
            return super.onOrderlineLongPress(ev, orderline);
        }
        return super.onOrderlineLongPress(ev, orderline);
    },
});

// ── 3. NoteButton + InternalNoteButton ────────────────────────────────────────
// Block customer-note edits on kitchen-sent lines.
patch(NoteButton.prototype, {
    async onClick() {
        const selectedLine = this.pos.getOrder()?.getSelectedOrderline();
        if (selectedLine?.isKitchenSent() && _isMinimalCashier(this.pos)) {
            const ok = await _applyManagerOverride(this);
            if (!ok) {
                return { confirmed: false };
            }
            return super.onClick();
        }
        return super.onClick();
    },
});

// InternalNoteButton overrides onClick() directly on its own prototype so the
// NoteButton patch above never fires for it — patch it separately.
patch(InternalNoteButton.prototype, {
    async onClick() {
        const selectedLine = this.pos.getOrder()?.getSelectedOrderline();
        if (selectedLine?.isKitchenSent() && _isMinimalCashier(this.pos)) {
            const ok = await _applyManagerOverride(this);
            if (!ok) {
                return { confirmed: false };
            }
            return super.onClick();
        }
        return super.onClick();
    },
});
