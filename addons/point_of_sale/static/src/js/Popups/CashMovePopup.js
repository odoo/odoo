/** @odoo-module */

import { AbstractAwaitablePopup } from "@point_of_sale/js/Popups/AbstractAwaitablePopup";
import { parse } from "web.field_utils";

const { useRef, useState, onMounted } = owl;

export class CashMovePopup extends AbstractAwaitablePopup {
    static template = "point_of_sale.CashMovePopup";

    setup() {
        super.setup();
        this.state = useState({
            inputType: "out", // '' | 'in' | 'out'
            inputAmount: "",
            inputReason: "",
            errorMessage: "",
        });
        this.inputAmountRef = useRef("input-amount-ref");
        onMounted(() => this.inputAmountRef.el.focus());
    }
    confirm() {
        try {
            parse.float(this.state.inputAmount);
        } catch {
            this.state.errorMessage = this.env._t("Invalid amount");
            return;
        }
        if (this.state.inputAmount < 0) {
            this.state.errorMessage = this.env._t("Insert a positive amount");
            return;
        }
        return super.confirm();
    }
    _onAmountKeypress(event) {
        if (["-", "+"].includes(event.key)) {
            event.preventDefault();
        }
    }
    onClickButton(type) {
        this.state.inputType = type;
        this.state.errorMessage = "";
        this.inputAmountRef.el.focus();
    }
    getPayload() {
        return {
            amount: parse.float(this.state.inputAmount),
            reason: this.state.inputReason.trim(),
            type: this.state.inputType,
        };
    }
}
