/** @odoo-module */

import * as Numpad from "@point_of_sale/../tests/tours/helpers/NumpadTourMethods";

export function clickPaymentMethod(name) {
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
export function clickPaymentlineDelButton(name, amount, mobile = false) {
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
export function clickPaymentline(name, amount) {
    return [
        {
            content: `click ${name} paymentline with ${amount} amount`,
            trigger: `.paymentlines .paymentline .payment-infos:contains("${name}"):has(.payment-amount:contains("${amount}"))`,
        },
    ];
}
export function clickEmailButton() {
    return [
        {
            content: `click email button`,
            trigger: `.payment-buttons .js_email`,
        },
    ];
}
export function clickInvoiceButton() {
    return [{ content: "click invoice button", trigger: ".payment-buttons .js_invoice" }];
}
export function clickValidate() {
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
 *  PaymentScreen.enterPaymentLineAmount("Cash", "70"),
 *  PaymentScreen.remainingIs("2.0"),
 *  PaymentScreen.pressNumpad("0"), <- desktop: add a 0
 *  PaymentScreen.fillPaymentLineAmountMobile("Cash", "700"), <- mobile: rewrite the amount
 *  PaymentScreen.remainingIs("0.00"),
 *  PaymentScreen.changeIs("628.0"),
 *
 * @param {String} keys space-separated numpad keys
 */
export function pressNumpad(keys) {
    return keys.split(" ").map((key) => Numpad.click(key, { mobile: false }));
}
export function clickBack() {
    return [
        {
            content: "click back button",
            trigger: ".payment-screen .button.back",
        },
    ];
}
export function clickTipButton() {
    return [
        {
            trigger: ".payment-screen .button.js_tip",
        },
    ];
}
export function enterPaymentLineAmount(lineName, keys) {
    const numpadKeys = keys.split("").join(" ");
    return [...this.pressNumpad(numpadKeys), ...this.fillPaymentLineAmountMobile(lineName, keys)];
}
export function fillPaymentLineAmountMobile(lineName, keys) {
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

export function isShown() {
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
export function changeIs(amount) {
    return [
        {
            content: `change is ${amount}`,
            trigger: `.payment-status-change .amount:contains("${amount}")`,
            run: () => {},
        },
    ];
}
export function isInvoiceOptionSelected() {
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
export function remainingIs(amount) {
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
export function validateButtonIsHighlighted(isHighlighted = true) {
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
export function emptyPaymentlines(amountToPay) {
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
export function selectedPaymentlineHas(paymentMethodName, amount) {
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
export function totalIs(amount) {
    return [
        {
            content: `total is ${amount}`,
            trigger: `.total:contains("${amount}")`,
            run: () => {},
        },
    ];
}
export function totalDueIs(amount) {
    return [
        {
            content: `total due is ${amount}`,
            trigger: `.payment-status-total-due:contains("${amount}")`,
            run: () => {},
        },
    ];
}
export function pay(method, amount) {
    const steps = [];
    steps.push(...clickPaymentMethod(method));
    for (const char of amount.split("")) {
        steps.push(...pressNumpad(char));
    }
    steps.push(...validateButtonIsHighlighted());
    steps.push(...clickValidate());
    return steps;
}
