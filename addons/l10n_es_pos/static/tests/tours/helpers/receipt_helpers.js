/** @odoo-module */

import { ProductScreen } from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import { PaymentScreen } from "@point_of_sale/../tests/tours/helpers/PaymentScreenTourMethods";

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
        ...ProductScreen.do.clickPayButton(),
        ...PaymentScreen.do.clickPaymentMethod("Bank"),
        ...PaymentScreen.do.clickValidate(),
    ];
}
