import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as FeedbackScreen from "@point_of_sale/../tests/pos/tours/utils/feedback_screen_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_gcc_basic_receipt_title_hidden", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Whiteboard Pen"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
            FeedbackScreen.checkTicketData(
                {
                    orderlines: [
                        {
                            name: "Whiteboard Pen",
                            quantity: "1",
                        },
                    ],
                    total_amount: 3.68,
                    cssRules: [
                        {
                            css: ".pos-receipt-header",
                            text: "Simplified Tax Invoice / فاتورة ضريبية مبسطة",
                            negation: false,
                        },
                    ],
                },
                false // normal receipt mode
            ),
            FeedbackScreen.checkTicketData(
                {
                    orderlines: [
                        {
                            name: "Whiteboard Pen",
                            quantity: "1",
                        },
                    ],
                    cssRules: [
                        {
                            css: ".pos-receipt-header",
                            text: "Simplified Tax Invoice / فاتورة ضريبية مبسطة",
                            negation: true,
                        },
                    ],
                },
                true // basic receipt mode
            ),
            Chrome.endTour(),
        ].flat(),
});
