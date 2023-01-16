/** @odoo-module */

import { PosComponent } from "@point_of_sale/js/PosComponent";

/**
 * @prop {'quantity' | 'price' | 'discount'} activeMode
 * @prop {Array<'quantity' | 'price' | 'discount'>} disabledModes
 * @prop {boolean} disableSign
 * @event set-numpad-mode - triggered when mode button is clicked
 * @event numpad-click-input - triggered when numpad button is clicked
 */
export class NumpadWidget extends PosComponent {
    static template = "NumpadWidget";
    static defaultProps = {
        disabledModes: [],
        disableSign: false,
    };

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
        this.trigger("set-numpad-mode", { mode });
    }
    sendInput(key) {
        this.trigger("numpad-click-input", { key });
    }
    get decimalSeparator() {
        return this.env._t.database.parameters.decimal_point;
    }
}
