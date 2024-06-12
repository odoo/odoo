/** @odoo-module */

import * as Order from "@point_of_sale/../tests/tours/helpers/generic_components/OrderWidgetMethods";

export function clickOrderline(productName) {
    return Order.hasLine({ productName, run: "click" });
}
export function clickBack() {
    return [
        {
            content: "click back button",
            trigger: `.splitbill-screen .button.back`,
        },
    ];
}
export function clickPay() {
    return [
        {
            content: "click pay button",
            trigger: `.splitbill-screen .pay-button .button`,
        },
    ];
}

export function orderlineHas(name, totalQuantity, splitQuantity) {
    return Order.hasLine({
        productName: name,
        quantity: splitQuantity != 0 ? `${splitQuantity} / ${totalQuantity}` : totalQuantity,
    });
}
export function subtotalIs(amount) {
    return [
        {
            content: `total amount of split is '${amount}'`,
            trigger: `.splitbill-screen .order-info .subtotal:contains("${amount}")`,
        },
    ];
}
