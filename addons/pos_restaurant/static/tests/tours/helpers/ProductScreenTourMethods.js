/** @odoo-module */

import * as Order from "@point_of_sale/../tests/tours/helpers/generic_components/OrderWidgetMethods";
import * as ProductScreen from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";

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
export function OrderButtonNotContain(data) {
    const steps = [
        {
            content: "check order button not contain data",
            trigger: `.product-screen .submit-order:not(:contains("${data}"))`,
            run: function () {}, // it's a check
            mobile: false,
        },
    ];
    return steps;
}
