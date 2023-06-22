/** @odoo-module */

import { createTourMethods } from "@point_of_sale/../tests/tours/helpers/utils";
import { Numpad } from "@point_of_sale/../tests/tours/helpers/NumpadTourMethods";

class Do {
    clickPaymentMethod(name) {
        return [
            {
                content: `click '${name}' payment method`,
                trigger: `.paymentmethods .button.paymentmethod:contains("${name}")`,
            },
        ];
    }

    /**
     * Delete the paymentline having the given payment method name and amount.
     * @param {String} name payment method
     * @param {String} amount
     */
    clickPaymentlineDelButton(name, amount, mobile = false) {
        return [
            {
                content: `delete ${name} paymentline with ${amount} amount`,
                trigger: `.paymentlines .paymentline .payment-infos:contains("${name}"):has(.payment-amount:contains("${amount}")) ~ .delete-button`,
            },
        ];
    }

    /**
     * Click the paymentline having the given payment method name and amount.
     * @param {String} name payment method
     * @param {String} amount
     */
    clickPaymentline(name, amount) {
        return [
            {
                content: `click ${name} paymentline with ${amount} amount`,
                trigger: `.paymentlines .paymentline .payment-infos:contains("${name}"):has(.payment-amount:contains("${amount}"))`,
            },
        ];
    }

    clickEmailButton() {
        return [
            {
                content: `click email button`,
                trigger: `.payment-buttons .js_email`,
            },
        ];
    }

    clickInvoiceButton() {
        return [{ content: "click invoice button", trigger: ".payment-buttons .js_invoice" }];
    }

    clickValidate() {
        return [
            {
                content: "validate payment",
                trigger: `.payment-screen .button.next.highlight`,
                mobile: false,
            },
            {
                content: "validate payment",
                trigger: `.payment-screen .btn-switchpane:contains('Validate')`,
                mobile: true,
            },
        ];
    }

    /**
     * Press the numpad in sequence based on the given space-separated keys.
     * Note: Maximum of 2 characters because NumberBuffer only allows 2 consecutive
     * fast inputs. Fast inputs is the case in tours. This method is only for the
     * desktop environment. The mobile environment doesn't work exactly the same way
     * so we have to call fillPaymentLineAmountMobile to have the same behaviour.
     *
     * e.g. :
     *  PaymentScreen.do.enterPaymentLineAmount("Cash", "70");
     *  PaymentScreen.check.remainingIs("2.0");
     *  PaymentScreen.do.pressNumpad("0"); <- desktop: add a 0
     *  PaymentScreen.do.fillPaymentLineAmountMobile("Cash", "700"); <- mobile: rewrite the amount
     *  PaymentScreen.check.remainingIs("0.00");
     *  PaymentScreen.check.changeIs("628.0");
     *
     * @param {String} keys space-separated numpad keys
     */
    pressNumpad(keys) {
        return keys.split(" ").map((key) => Numpad.click(key, { mobile: false }));
    }

    clickBack() {
        return [
            {
                content: "click back button",
                trigger: ".payment-screen .button.back",
            },
        ];
    }

    clickTipButton() {
        return [
            {
                trigger: ".payment-screen .button.js_tip",
            },
        ];
    }

    enterPaymentLineAmount(lineName, keys) {
        const numpadKeys = keys.split("").join(" ");
        return [
            ...this.pressNumpad(numpadKeys),
            ...this.fillPaymentLineAmountMobile(lineName, keys),
        ];
    }

    fillPaymentLineAmountMobile(lineName, keys) {
        return [
            {
                content: "click payment line",
                trigger: `.paymentlines .paymentline .payment-infos:contains("${lineName}")`,
                mobile: true,
            },
            {
                content: `'${keys}' inputed in the number popup`,
                trigger: ".popup .payment-input-number",
                run: `text ${keys}`,
                mobile: true,
            },
            {
                content: "click confirm button",
                trigger: ".popup .footer .confirm",
                mobile: true,
            },
        ];
    }
}

class Check {
    isShown() {
        return [
            {
                content: "payment screen is shown",
                trigger: ".pos .payment-screen",
                run: () => {},
            },
        ];
    }
    /**
     * Check if change is the provided amount.
     * @param {String} amount
     */
    changeIs(amount) {
        return [
            {
                content: `change is ${amount}`,
                trigger: `.payment-status-change .amount:contains("${amount}")`,
                run: () => {},
            },
        ];
    }
    isInvoiceOptionSelected() {
        return [
            {
                content: "Invoice option is selected",
                trigger: ".payment-buttons .js_invoice.highlight",
                isCheck: true,
            },
        ];
    }

    /**
     * Check if the remaining is the provided amount.
     * @param {String} amount
     */
    remainingIs(amount) {
        return [
            {
                content: `remaining amount is ${amount}`,
                trigger: `.payment-status-remaining .amount:contains("${amount}")`,
                run: () => {},
            },
        ];
    }

    /**
     * Check if validate button is highlighted.
     * @param {Boolean} isHighlighted
     */
    validateButtonIsHighlighted(isHighlighted = true) {
        return [
            {
                content: `validate button is ${isHighlighted ? "highlighted" : "not highligted"}`,
                trigger: isHighlighted
                    ? `.payment-screen .button.next.highlight`
                    : `.payment-screen .button.next:not(:has(.highlight))`,
                run: () => {},
                mobile: false,
            },
            {
                content: `validate button is ${isHighlighted ? "highlighted" : "not highligted"}`,
                trigger: isHighlighted
                    ? `.payment-screen .btn-switchpane:not(.secondary):contains('Validate')`
                    : `.payment-screen .btn-switchpane.secondary:contains('Validate')`,
                run: () => {},
                mobile: true,
            },
        ];
    }

    /**
     * Check if the paymentlines are empty. Also provide the amount to pay.
     * @param {String} amountToPay
     */
    emptyPaymentlines(amountToPay) {
        return [
            {
                content: `there are no paymentlines`,
                trigger: `.paymentlines-empty`,
                run: () => {},
            },
            {
                content: `amount to pay is '${amountToPay}'`,
                trigger: `.paymentlines-empty .total:contains("${amountToPay}")`,
                run: () => {},
            },
        ];
    }

    /**
     * Check if the selected paymentline has the given payment method and amount.
     * @param {String} paymentMethodName
     * @param {String} amount
     */
    selectedPaymentlineHas(paymentMethodName, amount) {
        return [
            {
                content: `line paid via '${paymentMethodName}' is selected`,
                trigger: `.paymentlines .paymentline.selected .payment-name:contains("${paymentMethodName}")`,
                run: () => {},
            },
            {
                content: `amount tendered in the line is '${amount}'`,
                trigger: `.paymentlines .paymentline.selected .payment-amount:contains("${amount}")`,
                run: () => {},
            },
        ];
    }
    totalIs(amount) {
        return [
            {
                content: `total is ${amount}`,
                trigger: `.total:contains("${amount}")`,
                run: () => {},
            },
        ];
    }
    totalDueIs(amount) {
        return [
            {
                content: `total due is ${amount}`,
                trigger: `.payment-status-total-due:contains("${amount}")`,
                run: () => {},
            },
        ];
    }
}

class Execute {
    pay(method, amount) {
        const steps = [];
        steps.push(...this._do.clickPaymentMethod(method));
        for (const char of amount.split("")) {
            steps.push(...this._do.pressNumpad(char));
        }
        steps.push(...this._check.validateButtonIsHighlighted());
        steps.push(...this._do.clickValidate());
        return steps;
    }
}

// FIXME: this is a horrible hack to export an object as named exports.
// eslint-disable-next-line no-undef
Object.assign(__exports, createTourMethods("PaymentScreen", Do, Check, Execute));
