import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as FeedbackScreen from "@point_of_sale/../tests/pos/tours/utils/feedback_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as Numpad from "@point_of_sale/../tests/generic_helpers/numpad_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("l10nFrPosCertSelfInvoicingTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Desk Pad"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
            FeedbackScreen.checkTicketData({
                cssRules: [
                    {
                        css: ".pos-receipt #posqrcode",
                    },
                ],
            }),
        ].flat(),
});

registry.category("web_tour.tours").add("test_correct_old_price_upon_price_change_fr", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Desk Pad"),
            ProductScreen.selectedOrderlineHas("Desk Pad", "1", "1.98"),
            Numpad.click("Price"),
            Numpad.isActive("Price"),
            Numpad.click("5"),
            ProductScreen.selectedOrderlineHas("Desk Pad", "1", "5.00"),
            {
                content: "Old unit price is correctly shown",
                trigger: ".order-container .orderline.selected:has(.oldPrice:contains(1.98))",
            },
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
            FeedbackScreen.checkTicketData({
                orderlines: [
                    {
                        name: "Desk Pad",
                        cssRules: [{ css: ".oldPrice", text: "1.98" }],
                    },
                ],
            }),
        ].flat(),
});
