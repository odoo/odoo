/** @odoo-module */

import * as ProductScreen from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import * as PaymentScreen from "@point_of_sale/../tests/tours/helpers/PaymentScreenTourMethods";

export function checkSimplifiedInvoiceNumber(number) {
    return [
        {
            content: "verify that the simplified invoice number appears correctly on the receipt",
            trigger: `.receipt-screen .simplified-invoice-number:contains('${number}')`,
            isCheck: true,
        },
    ];
}

export function pay() {
    return [
        ...ProductScreen.clickPayButton(),
        ...PaymentScreen.clickPaymentMethod("Bank"),
        ...PaymentScreen.clickValidate(),
    ];
}
