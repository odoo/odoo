/** @odoo-module */

import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";

/**
 * @prop {'quantity' | 'price' | 'discount'} activeMode
 * @prop {Array<'quantity' | 'price' | 'discount'>} disabledModes
 * @prop {boolean} disableSign
 */
export class NumpadWidget extends Component {
    static template = "NumpadWidget";
    static defaultProps = {
        disabledModes: [],
        disableSign: false,
    };
    setup() {
        this.numberBuffer = useService("number_buffer");
        this.numberBuffer.use({
            triggerAtInput: (event) => this.props.updateSelectedOrderline(event),
            useWithBarcode: true,
        });
    }
    get hasPriceControlRights() {
        return (
            this.env.pos.cashierHasPriceControlRights() &&
            !this.props.disabledModes.includes("price")
        );
    }
    get hasManualDiscount() {
        return (
            this.env.pos.config.manual_discount && !this.props.disabledModes.includes("discount")
        );
    }
    changeMode(mode) {
        if (!this.hasPriceControlRights && mode === "price") {
            return;
        }
        if (!this.hasManualDiscount && mode === "discount") {
            return;
        }
        this.numberBuffer.capture();
        this.numberBuffer.reset();
        this.env.pos.numpadMode = mode;
    }
    sendInput(key) {
        this.numberBuffer.sendKey(key);
    }
    get decimalSeparator() {
        return this.env._t.database.parameters.decimal_point;
    }
}
