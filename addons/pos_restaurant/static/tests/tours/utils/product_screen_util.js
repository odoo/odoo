/** @odoo-module */

import * as Order from "@point_of_sale/../tests/tours/utils/generic_components/order_widget_util";
import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";

export function clickOrderButton() {
    return [
        {
            content: "click order button",
            trigger: ".actionpad .submit-order",
        },
    ];
}
export function checkOrderlinesHaveNoChange() {
    return Order.checkDoesNotHaveLine({ withClass: ".has-change" });
}
export function checkOrderlineIsToOrder(name) {
    return Order.hasLine({
        productName: name,
        withClass: ".has-change.text-success.border-start.border-success.border-4",
    });
}
export function checkOrderlineIsToSkip(name) {
    return Order.hasLine({
        withClass: ".skip-change.text-primary.border-start.border-primary.border-4",
        productName: name,
    });
}
export function checkGuestNumberIs(num) {
    return [
        {
            content: `guest number is ${num}`,
            trigger: ProductScreen.controlButtonTrigger("Guests") + `:contains(${num})`,
            run: function () {}, // it's a check
        },
    ];
}
export function checkOrderBtnIsPresent() {
    return [
        {
            content: "Order button is here",
            trigger: ".actionpad .button.submit-order",
            run: function () {}, // it's a check
        },
    ];
}
