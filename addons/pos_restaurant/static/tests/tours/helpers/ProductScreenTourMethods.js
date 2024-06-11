/** @odoo-module */

import * as Order from "@point_of_sale/../tests/tours/helpers/generic_components/OrderWidgetMethods";
import * as ProductScreen from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";

<<<<<<< HEAD
||||||| parent of 82b73bd0779d (temp)
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
=======
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
>>>>>>> 82b73bd0779d (temp)
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
export function guestNumberIs(num) {
    return [
        {
            content: `guest number is ${num}`,
            trigger: ProductScreen.controlButtonTrigger("Guests") + `:contains(${num})`,
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
export function tableNameShown(table_name) {
    return [
        {
            content: "Table name is shown",
            trigger: `.table-name:contains(${table_name})`,
        },
    ];
}
