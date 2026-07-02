// Part of Odoo. See LICENSE file for full copyright and licensing details.

import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { patch } from "@web/core/utils/patch";

patch(OrderSummary.prototype, {
    _l10nPhGetTrackedLine(line) {
        return line.combo_parent_id || line;
    },

    clickLine(ev, orderline) {
        if (this.pos.isPhilippinesCompany()) {
            this.pos.l10nPhFlushPendingDecrease();
        }
        return super.clickLine(ev, orderline);
    },

    async updateSelectedOrderline({ buffer }) {
        if (!this.pos.isPhilippinesCompany()) {
            return super.updateSelectedOrderline(...arguments);
        }
        const selectedLine = this.currentOrder?.getSelectedOrderline();
        const trackedLine = selectedLine && this._l10nPhGetTrackedLine(selectedLine);
        if (!this.pos.config.module_pos_hr || !trackedLine || this.pos.numpadMode !== "quantity") {
            await this.pos.l10nPhFlushPendingDecrease();
            return super.updateSelectedOrderline(...arguments);
        }
        const val = buffer === null ? "remove" : buffer;
        const numericValue = Number(val);
        if (val === "remove" || val === "" || numericValue === 0) {
            const oldQuantity = this.pos._l10nPhPending?.oldQuantity ?? trackedLine.getQuantity();
            this.pos.l10nPhClearPendingDecrease();
            this.numberBuffer.reset();
            await this.pos._l10nPhRequestLineVoidWithQty(trackedLine, oldQuantity);
            return;
        }
        const pending = this.pos._l10nPhPending;
        if (!pending || pending.line !== trackedLine) {
            this.pos.l10nPhSetPendingDecrease(trackedLine, trackedLine.getQuantity());
        }
        const originalQty = this.pos._l10nPhPending.oldQuantity;
        if (!Number.isFinite(numericValue) || numericValue < 0 || numericValue >= originalQty) {
            this.pos.l10nPhClearPendingDecrease();
            return super.updateSelectedOrderline(...arguments);
        }
        super._setValue(val);
    },
});
