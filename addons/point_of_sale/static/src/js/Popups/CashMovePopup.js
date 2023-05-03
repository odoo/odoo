/** @odoo-module */

import AbstractAwaitablePopup from "@point_of_sale/js/Popups/AbstractAwaitablePopup";
import Registries from "@point_of_sale/js/Registries";
import { _lt } from "@web/core/l10n/translation";
import { parse } from "web.field_utils";
import { useValidateCashInput } from "@point_of_sale/js/custom_hooks";

const { useRef, useState, onMounted } = owl;

class CashMovePopup extends AbstractAwaitablePopup {
    setup() {
        super.setup();
        this.state = useState({
            inputType: "out", // '' | 'in' | 'out'
            inputAmount: "",
            inputReason: "",
            errorMessage: "",
            parsedAmount: 0,
        });
        this.inputAmountRef = useRef("input-amount-ref");
        useValidateCashInput('input-amount-ref');
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
    handleInputChange() {
        if (this.inputAmountRef.el.classList.contains('invalid-cash-input')) return;
        this.state.parsedAmount = parse.float(this.state.inputAmount);
    }
}
CashMovePopup.template = "point_of_sale.CashMovePopup";
CashMovePopup.defaultProps = {
    cancelText: _lt("Cancel"),
    title: _lt("Cash In/Out"),
};

Registries.Component.add(CashMovePopup);

export default CashMovePopup;
