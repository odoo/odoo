import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";

export function checkSimplifiedInvoiceNumber(number) {
    return [
        {
            content: "verify that the simplified invoice number appears correctly on the receipt",
            trigger: `.receipt-screen .simplified-invoice-number:contains('${number}')`,
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

export function checkCompanyState(state) {
    return [
        {
            content: "verify that the company state is on the receipt",
            trigger: `.pos-receipt-container div:contains('(${state})')`,
        },
    ];
}
