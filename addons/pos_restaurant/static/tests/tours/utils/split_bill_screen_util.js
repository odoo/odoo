import * as Order from "@point_of_sale/../tests/generic_helpers/order_widget_util";

export function clickOrderline(productName) {
    return Order.hasLine({ productName, run: "click" });
}
export function clickBack() {
    return [
        {
            content: "click back button",
            trigger: `.splitbill-screen .button.back`,
            run: "click",
        },
    ];
}
export function clickButton(name) {
    return [
        {
            content: `click '${name}' button`,
            trigger: `.splitbill-screen .pay-button button:contains("${name}")`,
            run: "click",
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
            run: "click",
        },
    ];
}
