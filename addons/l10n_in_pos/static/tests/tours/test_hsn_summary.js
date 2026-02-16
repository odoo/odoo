import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as FeedbackScreen from "@point_of_sale/../tests/pos/tours/utils/feedback_screen_util";
import * as TicketScreen from "@point_of_sale/../tests/pos/tours/utils/ticket_screen_util";
import { registry } from "@web/core/registry";

export function addDocument(documentParams) {
    const steps = [];
    for (const values of documentParams) {
        steps.push(...ProductScreen.addOrderline(values.product, values.quantity));
        if (values.discount) {
            steps.push(ProductScreen.addDiscount(values.discount));
        }
    }
    steps.push(ProductScreen.clickPayButton());
    return steps;
}

registry.category("web_tour.tours").add("test_l10n_in_hsn_summary_pos", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ...addDocument([
                { product: "product_1_1", quantity: "2" },
                { product: "product_1_2", quantity: "1" },
                { product: "product_1_3", quantity: "5" },
                { product: "product_1_4", quantity: "2" },
                { product: "product_1_5", quantity: "1" },
                { product: "product_1_6", quantity: "5" },
            ]),
            PaymentScreen.totalIs("5,129.0"),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.remainingIs("0.0"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
            FeedbackScreen.checkTicketData({
                cssRules: [
                    {
                        css: ".l10n_in_hsn_summary_table tr:nth-child(3) td:nth-child(3)",
                        text: "57.50",
                    },
                    {
                        css: ".l10n_in_hsn_summary_table tr:nth-child(3) td:nth-child(4)",
                        text: "57.50",
                    },
                    {
                        css: ".l10n_in_hsn_summary_table tr:nth-child(4) td:nth-child(3)",
                        text: "207.00",
                    },
                    {
                        css: ".l10n_in_hsn_summary_table tr:nth-child(4) td:nth-child(4)",
                        text: "207.00",
                    },
                ],
            }),
        ].flat(),
});

registry.category("web_tour.tours").add("test_refund_order_receipt", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
            FeedbackScreen.clickNextOrder(),
            ProductScreen.isShown(),
            Chrome.clickOrders(),
            TicketScreen.selectFilter("Paid"),
            TicketScreen.selectOrder("1001"),
            TicketScreen.confirmRefund(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
            Chrome.endTour(),
        ].flat(),
});
