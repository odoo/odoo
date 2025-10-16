/* global posmodel */

import * as Numpad from "@point_of_sale/../tests/generic_helpers/numpad_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as PartnerList from "@point_of_sale/../tests/pos/tours/utils/partner_list_util";
import * as NumberPopup from "@point_of_sale/../tests/generic_helpers/number_popup_util";
import { negate } from "@point_of_sale/../tests/generic_helpers/utils";

const _getPaymentlineSelector = ({ name, amount, nth, selected } = {}) => {
    const selectedSelector = selected ? ".selected" : "";
    const nameSelector = name ? `:has(.payment-name:contains("${name}"))` : "";
    const amountSelector = amount ? `:has(.payment-amount:contains("${amount}"))` : "";
    const nthSelector = nth ? `:nth-of-type(${nth})` : "";

    return `.paymentlines .paymentline${nthSelector}${selectedSelector}${nameSelector}${amountSelector}`;
};

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
export function clickCancelButton() {
    return [
        {
            content: "Cancel the ongoing payment request currently being processed.",
            trigger: ".paymentline_status_actions .paymentline_status_actions_button_cancel",
            run: "click",
        },
    ];
}
export function clickRetryButton() {
    return [
        {
            content: "Retry sending the payment request using the payment terminal.",
            trigger: ".paymentline_status_actions .paymentline_status_actions_button_retry",
            run: "click",
        },
    ];
}
export function clickRefundButton() {
    return [
        {
            content: "Initiate a refund request for the selected order.",
            trigger: ".paymentline_status_actions .paymentline_status_actions_button_refund",
            run: "click",
        },
    ];
}
export function clickForceDoneButton() {
    return [
        {
            content: "Force mark the payment as completed, regardless of its current status.",
            trigger: ".paymentline_status_actions .paymentline_status_actions_button_force_done",
            run: "click",
        },
    ];
}

export function hasActionState(actionStateId) {
    return {
        content: `check if paymentline has the action state '${actionStateId}'`,
        trigger: `.paymentline_status .paymentline_status_title_${actionStateId}`,
    };
}

/**
 * Click the paymentline having the given payment method name and amount.
 * @param {String} name payment method
 * @param {String} amount
 */
export function clickPaymentline(name, amount, nth, selected) {
    return [
        {
            content: `click ${name} paymentline with ${amount} amount`,
            trigger: _getPaymentlineSelector({ name, amount, nth, selected }) + " .payment-infos",
            run: "click",
        },
    ];
}
export function countPaymentlinesIs(count) {
    return [
        {
            content: `there are ${count} paymentlines`,
            trigger: `.paymentlines .paymentline:nth-of-type(${count})`,
            run: () => {
                const paymentlines = document.querySelectorAll(".paymentlines .paymentline");
                if (paymentlines.length !== count) {
                    throw new Error(
                        `Expected ${count} paymentlines, but found ${paymentlines.length}.`
                    );
                }
            },
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
            content: "validate payment",
            trigger: `.payment-screen button.validation-button.next`,
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
    const { remaining = null, change = null, amount = null, nth = null } = options;
    const step = [
        ...clickNumpad(keys.split("").join(" ")),
        ...fillPaymentLineAmountMobile(lineName, keys, nth),
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
export function fillPaymentLineAmountMobile(lineName, keys, nth = null) {
    const nthSelector = nth ? `:nth-of-type(${nth})` : "";
    return [
        {
            isActive: ["mobile"],
            content: "click payment line",
            trigger: `.paymentlines .paymentline${nthSelector} .payment-infos:contains("${lineName}")`,
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
            trigger: `.payment-status-amount .amount:contains("${amount}")`,
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
    const step = `.payment-status-amount .amount:contains("${amount}")`;
    // If amount is 0 we do NOT show the payment status on the PaymentScreen
    if (!parseFloat(amount)) {
        return [{ trigger: negate(step) }];
    }
    return [
        {
            content: `remaining amount is ${amount}`,
            trigger: step,
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
            content: `validate button is ${isHighlighted ? "highlighted" : "not highlighted"}`,
            trigger: isHighlighted
                ? `.payment-screen button.validation-button.next.highlight`
                : `.payment-screen button.validation-button.next:not(:has(.highlight))`,
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

export function clickCustomer(name, pressEnter = false) {
    return [...PartnerList.searchCustomerValue(name, pressEnter), PartnerList.clickPartner(name)];
}

export function shippingLaterHighlighted() {
    return {
        content: "Shipping later button is highlighted",
        trigger: ".button:contains('Ship Later').highlight",
    };
}

// This method is used to simulate payment with a payment terminal, before using terminal the order
// is synced to ensure that the order is up-to-date and ready for payment.
export function syncCurrentOrder() {
    return [
        {
            content: "sync current order",
            trigger: "body",
            run: async () => {
                const currentOrder = posmodel.getOrder();
                const order = await posmodel.syncAllOrders({ orders: [currentOrder] });

                if (!order[0].isSynced) {
                    throw new Error("Order ID is not a number after sync.");
                }
            },
        },
    ];
}

/**
 * Tell if the tip container is shown.
 */
export function tipContainerIsShown(boolean = true) {
    return {
        content: `tip container is ${boolean ? "shown" : "not shown"}`,
        trigger: boolean
            ? ".payment-screen .tip-container"
            : negate(".tip-container", ".payment-screen"),
    };
}

export function isInvoiceButtonUnchecked() {
    return [
        {
            content: "check invoice button is not highlighted",
            trigger: ".js_invoice:not(.highlight)",
        },
    ];
}

// ----- QR POPUP ----- //
export function qrPopupIsShown(amount) {
    const amountSelector = amount ? ` .qr-code-amount:contains('${amount}')` : "";
    return {
        content: "QR code popup is shown",
        trigger: `.modal .modal-content.o_qr_popup${amountSelector}`,
    };
}

export function qrPopupIsNotShown() {
    return {
        content: "QR code popup is not shown",
        trigger: negate(".modal .modal-content.o_qr_popup"),
    };
}

export function confirmQrPopup() {
    return {
        content: "confirm QR code popup",
        trigger: ".o_qr_popup .qr-code-popup-footer .confirm-button",
        run: "click",
    };
}

export function closeQrPopup() {
    return {
        content: "close QR code popup",
        trigger: ".o_qr_popup .qr-code-popup-footer .cancel-button",
        run: "click",
    };
}

export function showQrPopup(opts) {
    return [
        qrPopupIsNotShown(),
        {
            content: `open QR code popup from paymentline (opts: ${JSON.stringify(opts)})`,
            trigger: ` ${_getPaymentlineSelector(opts)} .paymentline_show_qr_code`,
            run: "click",
        },
    ];
}

export function showQrPopupIsDisabled(opts) {
    return {
        content: `open QR code popup from paymentline is disabled (opts: ${JSON.stringify(opts)})`,
        trigger: ` ${_getPaymentlineSelector(opts)} .paymentline_show_qr_code[disabled]`,
    };
}
