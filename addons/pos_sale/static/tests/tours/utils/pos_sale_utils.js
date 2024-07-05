/** @odoo-module */

import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as Numpad from "@point_of_sale/../tests/tours/utils/numpad_util";

function selectNthOrder(n) {
    return [
        ProductScreen.clickControlButton("Quotation/Order"),
        {
            content: `select nth order`,
            trigger: `.modal:not(.o_inactive_modal) table.o_list_table tbody tr.o_data_row:nth-child(${n}) td`,
            in_modal: false,
            run: "click",
        },
    ];
}

export function settleNthOrder(n) {
    return [
        ...selectNthOrder(n),
        {
            content: `Choose to settle the order`,
            trigger: `.modal:not(.o_inactive_modal) .selection-item:contains('Settle the order')`,
            in_modal: false,
            run: "click",
        },
        {
            trigger: "body:not(:has(.modal))",
        },
    ];
}

export function downPaymentFirstOrder() {
    return [
        ...selectNthOrder(1),
        {
            content: `click on select the order`,
            trigger: `.selection-item:contains('Apply a down payment')`,
            run: "click",
        },
        Numpad.click("+10"),
        Dialog.confirm(),
    ];
}
