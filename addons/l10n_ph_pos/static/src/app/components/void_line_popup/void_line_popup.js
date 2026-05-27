// Part of Odoo. See LICENSE file for full copyright and licensing details.

import { Component, proxy } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";

export class L10nPhPosVoidLinePopup extends Component {
    static template = "l10n_ph_pos.PosVoidLinePopup";
    static components = { Dialog };
    static props = {
        line: Object,
        order: Object,
        actionType: { type: String, optional: true },
        oldQuantity: { type: Number, optional: true },
        newQuantity: { type: Number, optional: true },
        requirePasscode: { type: Boolean, optional: true },
        getPayload: Function,
        close: Function,
    };

    setup() {
        this.state = proxy({
            reason: "",
            passcode: "",
        });
    }

    get isQuantityDecrease() {
        return this.props.actionType === "quantity_decrease";
    }

    get title() {
        return this.isQuantityDecrease ? _t("Approve Quantity Decrease") : _t("Void Item");
    }

    get isValid() {
        return !this.requirePasscode || this.state.passcode.trim().length > 0;
    }

    get requirePasscode() {
        return this.props.requirePasscode ?? true;
    }

    get confirmLabel() {
        return this.isQuantityDecrease ? _t("Approve Change") : _t("Confirm Void");
    }

    get voidedLine() {
        const line = this.props.line;
        const oldQuantity = this.props.oldQuantity ?? line.getQuantity();
        const newQuantity = this.props.newQuantity ?? 0;
        const deltaQuantity = this.isQuantityDecrease ? oldQuantity - newQuantity : oldQuantity;
        const unitPriceExcl = oldQuantity ? line.priceExcl / oldQuantity : line.priceExcl;
        const unitPriceIncl = oldQuantity ? line.priceIncl / oldQuantity : line.priceIncl;
        const subtotal = unitPriceExcl * deltaQuantity;
        const total = unitPriceIncl * deltaQuantity;
        return {
            name: line.getFullProductName(),
            qty: deltaQuantity,
            oldQuantity,
            newQuantity,
            subtotal,
            tax: total - subtotal,
            total,
        };
    }

    get orderTotal() {
        return this.props.order.priceIncl;
    }

    get orderTax() {
        return this.props.order.amountTaxes;
    }

    formatCurrency(val) {
        return this.env.utils.formatCurrency(val);
    }

    confirm() {
        this.props.getPayload({
            actionType: this.props.actionType || "line_void",
            reason: this.state.reason.trim(),
            passcode: this.state.passcode.trim(),
        });
        this.props.close();
    }
}
