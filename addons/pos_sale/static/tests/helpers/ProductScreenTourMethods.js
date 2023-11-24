/** @odoo-module */

import * as Numpad from "@point_of_sale/../tests/tours/helpers/NumpadTourMethods";
import * as Dialog from "@point_of_sale/../tests/tours/helpers/DialogTourMethods";

export function clickQuotationButton() {
    return [
        {
            content: "click quotation button",
            trigger: ".o_sale_order_button",
        },
    ];
}
export function selectFirstOrder() {
    return [
        {
            content: `select order`,
            trigger: `.order-row .col.name:first`,
        },
        {
            content: `click on select the order`,
            trigger: `.selection-item:contains('Settle the order')`,
        },
    ];
}
export function selectNthOrder(n) {
    return [
        {
            content: `select order`,
            trigger: `.order-list .order-row:nth-child(${n})`,
        },
        {
            content: `click on select the order`,
            trigger: `.selection-item:contains('Settle the order')`,
        },
    ];
}
export function downPaymentFirstOrder() {
    return [
        {
            content: `select order`,
            trigger: `.order-row .col.name:first`,
        },
        {
            content: `click on select the order`,
            trigger: `.selection-item:contains('Apply a down payment')`,
        },
        Numpad.click("+10"),
        Dialog.confirm(),
    ];
}
