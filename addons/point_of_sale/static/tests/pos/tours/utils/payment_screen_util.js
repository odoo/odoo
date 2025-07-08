import * as Numpad from "@point_of_sale/../tests/generic_helpers/numpad_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as PartnerList from "@point_of_sale/../tests/pos/tours/utils/partner_list_util";
import * as NumberPopup from "@point_of_sale/../tests/generic_helpers/number_popup_util";

/**
 * Clicks on the payment method and then performs checks if necessary.
 *
 * @param {string} name - The name of the payment method to click on. This name is used to identify the corresponding element in the user interface.
 * @param {boolean} [isCheckNeeded=false] - Indicates whether additional checks are necessary after clicking on the payment method. If `true`, additional verification steps will be added to ensure that the expected changes (such as the remaining amount, change, or selected amount) are correctly applied.
 * @param {Object} [options={}] - An object containing additional options for the checks. The options include:
 *   @param {string|null} [options.remaining=null] - The expected remaining amount after selecting the payment method. If provided and `isCheckNeeded` is `true`, a check will be performed to ensure this remaining amount is correct.
 *   @param {string|null} [options.change=null] - The expected change amount after selecting the payment method. If provided and `isCheckNeeded` is `true`, a check will be performed to confirm this change amount.
 *   @param {string|null} [options.amount=null] - The specific amount associated with the selected payment method. If provided and `isCheckNeeded` is `true`, a check will ensure that the selected amount is correctly displayed.
 *
 *
 * @example
 * // Clicks on the "Cash" payment method without additional checks
 * clickPaymentMethod("Cash");
 *
 * // Clicks on the "Bank" payment method and checks the remaining amount and change
 * clickPaymentMethod("Cash", true, { remaining: "50.20", change: "10.50" });
 *
 * // Clicks on the "Cash" payment method and checks the amount to be paid
 * clickPaymentMethod("Cash", true, { amount: "10.20" });
 */
export function clickPaymentMethod(name, isCheckNeeded = false, options = {}) {
    const { remaining = null, change = null, amount = null } = options;

    const step = [
        {
            content: `click '${name}' payment method`,
            trigger: `.paymentmethods .button.paymentmethod .payment-name:contains("${name}")`,
            run: "click",
        },
    ];

    if (isCheckNeeded) {
        if (remaining) {
            step.push(...remainingIs(remaining));
        }
        if (change) {
            step.push(...changeIs(change));
        }
        if (amount) {
            step.push(...selectedPaymentlineHas(name, amount));
        }
    }

    return step;
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
            run: "click",
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
            run: "click",
        },
    ];
}
export function clickInvoiceButton() {
    return [
        {
            content: "click invoice button",
            trigger: ".payment-buttons .js_invoice",
            run: "click",
        },
    ];
}
export function clickValidate() {
    return [
        {
            isActive: ["desktop"],
            content: "validate payment",
            trigger: `.payment-screen .button.next.highlight`,
            run: "click",
        },
        {
            isActive: ["mobile"],
            content: "validate payment",
            trigger: `.payment-screen .btn-switchpane:contains('Validate')`,
            run: "click",
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
 *  PaymentScreen.clickNumpad("0"), <- desktop: add a 0
 *  PaymentScreen.fillPaymentLineAmountMobile("Cash", "700"), <- mobile: rewrite the amount
 *  PaymentScreen.remainingIs("0.00"),
 *  PaymentScreen.changeIs("628.0"),
 *
 * @param {String} keys space-separated numpad keys
 */
export function clickNumpad(keys) {
    return keys.split(" ").map((key) => ({ ...Numpad.click(key), isActive: ["desktop"] }));
}
export function clickBack() {
    return [
        {
            content: "click back button",
            trigger: ".back-button",
            run: "click",
        },
    ];
}
export function clickBackToProductScreen() {
    return [
        {
            content: "click back to product screen",
            trigger: ".payment-screen .back-button",
            run: "click",
        },
    ];
}
export function clickTipButton() {
    return [
        {
            trigger: ".payment-screen .button:contains('Tip')",
            run: "click",
        },
    ];
}
/**
 * Enter an amount for a specified payment line and then perform checks if necessary.
 *
 * This function performs the entry of an amount on a payment line in the user interface. It can also check for expected conditions such as the remaining amount, change, or the selected amount after the entry.
 *
 * @param {string} lineName - The name of the payment line where the amount needs to be entered. This name helps to identify the target payment line in the user interface.
 * @param {string} keys - The sequence of keys to simulate for the amount entry, in the form of a string where each character represents a key to press.
 * @param {boolean} [isCheckNeeded=false] - Indicates whether additional checks need to be performed after the amount entry.
 * @param {Object} [options={}] - An object containing additional options for checks. The options include:
 *   @param {string|null} [options.remaining=null] - The expected remaining amount after the amount is entered on the payment line. If provided and `isCheckNeeded` is `true`, a check will be performed to ensure this remaining amount is correct.
 *   @param {string|null} [options.change=null] - The expected change amount after the amount is entered on the payment line. If provided and `isCheckNeeded` is `true`, a check will be performed to confirm this change amount.
 *   @param {string|null} [options.amount=null] - The specific amount expected on the payment for this line after the entry. If provided and `isCheckNeeded` is `true`, a check will ensure that the selected amount is correctly displayed.
 *
 * @example
 * // Enter the amount "50" on the "Cash" payment line without additional checks
 * enterPaymentLineAmount("Cash", "50");
 *
 * @example
 * // Enter the amount "100" on the "Bank" payment line and check that the remaining amount is 50 and the change is 20
 * enterPaymentLineAmount("Bank", "100", true, { remaining: "50.0", change: "20.0" });
 */
export function enterPaymentLineAmount(lineName, keys, isCheckNeeded = false, options = {}) {
    const { remaining = null, change = null, amount = null } = options;
    const step = [
        ...clickNumpad(keys.split("").join(" ")),
        ...fillPaymentLineAmountMobile(lineName, keys),
    ];

    if (isCheckNeeded) {
        if (remaining) {
            step.push(...remainingIs(remaining));
        }
        if (change) {
            step.push(...changeIs(change));
        }
        if (amount) {
            step.push(...selectedPaymentlineHas(lineName, amount));
        }
    }

    return step;
}
export function fillPaymentLineAmountMobile(lineName, keys) {
    return [
        {
            isActive: ["mobile"],
            content: "click payment line",
            trigger: `.paymentlines .paymentline .payment-infos:contains("${lineName}")`,
            run: "click",
        },
        ...NumberPopup.enterValue(keys).map((step) => ({
            ...step,
            isActive: ["mobile"],
            run: "click",
        })),
        {
            ...Dialog.confirm(),
            isActive: ["mobile"],
            run: "click",
        },
    ];
}

export function isShown() {
    return [
        {
            content: "payment screen is shown",
            trigger: ".pos .payment-screen",
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
        },
    ];
}
export function isInvoiceOptionSelected() {
    return [
        {
            content: "Invoice option is selected",
            trigger: ".payment-buttons .js_invoice.highlight",
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
            isActive: ["desktop"],
            content: `validate button is ${isHighlighted ? "highlighted" : "not highligted"}`,
            trigger: isHighlighted
                ? `.payment-screen .button.next.highlight`
                : `.payment-screen .button.next:not(:has(.highlight))`,
        },
        {
            isActive: ["mobile"],
            content: `validate button is ${isHighlighted ? "highlighted" : "not highligted"}`,
            trigger: isHighlighted
                ? `.payment-screen .btn-switchpane:not(.secondary):contains('Validate')`
                : `.payment-screen .btn-switchpane.secondary:contains('Validate')`,
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
        },
        {
            content: `amount to pay is '${amountToPay}'`,
            trigger: `.paymentlines-empty .total:contains("${amountToPay}")`,
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
        },
        {
            content: `amount tendered in the line is '${amount}'`,
            trigger: `.paymentlines .paymentline.selected .payment-amount:contains("${amount}")`,
        },
    ];
}
export function totalIs(amount) {
    return [
        {
            content: `total is ${amount}`,
            trigger: `.total:contains("${amount}")`,
        },
    ];
}
export function pay(method, amount) {
    const steps = [];
    steps.push(...clickPaymentMethod(method));
    for (const char of amount.split("")) {
        steps.push(...clickNumpad(char));
    }
    steps.push(...validateButtonIsHighlighted());
    steps.push(...clickValidate());
    return steps;
}

export function isInvoiceButtonChecked() {
    return [
        {
            content: "check invoice button is checked",
            trigger: ".js_invoice.highlight",
        },
    ];
}

export function clickShipLaterButton() {
    return [
        {
            content: "click ship later button",
            trigger: ".button:contains('Ship Later')",
            run: "click",
        },
        {
            content: "click confirm button",
            trigger: ".btn:contains('Confirm')",
            run: "click",
        },
    ];
}

export function clickPartnerButton() {
    return [
        {
            content: "click customer button",
            trigger: "button.partner-button",
            run: "click",
        },
        {
            content: "partner screen is shown",
            trigger: `${PartnerList.clickPartner().trigger}`,
        },
    ];
}

export function clickCustomer(name) {
    return [PartnerList.clickPartner(name)];
}

export function shippingLaterHighlighted() {
    return {
        content: "Shipping later button is highlighted",
        trigger: ".button:contains('Ship Later').highlight",
    };
}
