/** @odoo-module */

import * as Order from "@point_of_sale/../tests/tours/helpers/generic_components/OrderWidgetMethods";

export function clickSplitBillButton() {
    return [
        {
            content: "click split bill button",
            trigger: ".control-buttons .control-button.order-split",
        },
    ];
}
export function clickTransferButton() {
    return [
        {
            content: "click transfer button",
            trigger: '.control-buttons .control-button span:contains("Transfer")',
        },
    ];
}
export function clickNoteButton() {
    return [
        {
            content: "click note button",
            trigger: '.control-buttons .control-button span:contains("Internal Note")',
        },
    ];
}
export function clickPrintBillButton() {
    return [
        {
            content: "click print bill button",
            trigger: ".control-buttons .control-button.order-printbill",
        },
        {
            content: "Close printing error",
            trigger: ".popup-error .cancel",
        },
    ];
}
export function clickSubmitButton() {
    return [
        {
            content: "click print bill button",
            trigger: '.control-buttons .control-button span:contains("Order")',
        },
    ];
}
export function clickGuestButton() {
    return [
        {
            content: "click guest button",
            trigger: '.control-buttons .control-button span:contains("Guests")',
        },
    ];
}
export function clickOrderButton() {
    return [
        {
            content: "click order button",
            trigger: ".actionpad .submit-order",
        },
    ];
}
export function orderlinesHaveNoChange() {
    return Order.doesNotHaveLine({ withClass: ".has-change" });
}
export function isPrintingError() {
    // because we don't have printer in the test.
    return [
        {
            content: "Cancel printing changes",
            trigger: ".modal-dialog .cancel",
        },
    ];
}
export function orderlineIsToOrder(name) {
    return Order.hasLine({
        productName: name,
        withClass: ".has-change.text-success.border-start.border-success.border-4",
    });
}
export function orderlineIsToSkip(name) {
    return Order.hasLine({
        withClass: ".skip-change.text-primary.border-start.border-primary.border-4",
        productName: name,
    });
}
export function guestNumberIs(numberInString) {
    return [
        {
            content: `guest number is ${numberInString}`,
            trigger: `.control-buttons .control-button span.control-button-number:contains(${numberInString})`,
            run: function () {}, // it's a check
        },
    ];
}
export function orderBtnIsPresent() {
    return [
        {
            content: "Order button is here",
            trigger: ".actionpad .button.submit-order",
            run: function () {}, // it's a check
        },
    ];
}
