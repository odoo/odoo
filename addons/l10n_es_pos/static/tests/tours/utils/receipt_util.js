import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as FeedbackScreen from "@point_of_sale/../tests/pos/tours/utils/feedback_screen_util";

export function checkSimplifiedInvoiceNumber(number) {
    return [
        ...FeedbackScreen.checkTicketData({
            cssRules: [
                {
                    css: ".simplified-invoice-number",
                    text: number,
                },
            ],
        }),
    ];
}

export function pay() {
    return [
        ...ProductScreen.clickPayButton(),
        ...PaymentScreen.clickPaymentMethod("Bank"),
        ...PaymentScreen.clickValidate(),
    ];
}
