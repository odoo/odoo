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
<<<<<<< HEAD
        return super.confirm();
    }
    _onAmountKeypress(event) {
        if (["-", "+"].includes(event.key)) {
            event.preventDefault();
||||||| parent of 920001e02e3 (temp)
        _onAmountKeypress(event) {
            if (event.key === '-') {
                event.preventDefault();
                this.state.inputAmount = this.state.inputType === 'out' ? this.state.inputAmount.substring(1) : `-${this.state.inputAmount}`;
                this.state.inputType = this.state.inputType === 'out' ? 'in' : 'out';
                this.handleInputChange();
            }
        }
        onClickButton(type) {
            let amount = this.state.inputAmount;
            if (type === 'in') {
                this.state.inputAmount = amount.charAt(0) === '-' ? amount.substring(1) : amount;
            } else {
                this.state.inputAmount = amount.charAt(0) === '-' ? amount : `-${amount}`;
            }
            this.state.inputType = type;
            this.state.inputHasError = false;
            this.inputAmountRef.el && this.inputAmountRef.el.focus();
            this.handleInputChange();
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
=======
        _onAmountKeypress(event) {
            if (event.key === '-') {
                event.preventDefault();
                this.state.inputAmount = this.state.inputType === 'out' ? this.state.inputAmount.substring(1) : `-${this.state.inputAmount}`;
                this.state.inputType = this.state.inputType === 'out' ? 'in' : 'out';
                this.handleInputChange();
            }
        }
        onClickButton(type) {
            let amount = this.state.inputAmount;
            if (type === 'in') {
                this.state.inputAmount = amount.charAt(0) === '-' ? amount.substring(1) : amount;
            } else {
                this.state.inputAmount = amount.charAt(0) === '-' ? amount : `-${amount}`;
            }
            this.state.inputType = type;
            this.state.inputHasError = false;
            this.inputAmountRef.el && this.inputAmountRef.el.focus();
            if (amount && amount !== '-') {
                this.handleInputChange();
            }
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
>>>>>>> 920001e02e3 (temp)
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
