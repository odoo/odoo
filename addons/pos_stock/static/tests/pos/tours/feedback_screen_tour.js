import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as StockPaymentScreen from "@pos_stock/../tests/pos/tours/utils/payment_screen_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as StockProductScreen from "@pos_stock/../tests/pos/tours/utils/product_screen_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as FeedbackScreen from "@point_of_sale/../tests/pos/tours/utils/feedback_screen_util";
import * as StockFeedbackScreen from "@pos_stock/../tests/pos/tours/utils/feedback_screen_util";
import { registry } from "@web/core/registry";
import * as NumberPopup from "@point_of_sale/../tests/generic_helpers/number_popup_util";
import * as Order from "@point_of_sale/../tests/generic_helpers/order_widget_util";
import * as Numpad from "@point_of_sale/../tests/generic_helpers/numpad_util";
import * as OfflineUtil from "@point_of_sale/../tests/generic_helpers/offline_util";
import { inLeftSide } from "@point_of_sale/../tests/pos/tours/utils/common";

registry.category("web_tour.tours").add("StockFeedbackScreenTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            OfflineUtil.setOfflineMode(),
            ProductScreen.addOrderline("Letter Tray", "10", "5"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner Full"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.validateButtonIsHighlighted(true),
            StockPaymentScreen.clickShipLaterButton(),
            StockPaymentScreen.shippingLaterHighlighted(),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
            StockFeedbackScreen.checkTicketData({
                total_amount: "55.00", // letter tray has 10% tax (search SRC)
                cashier_name: "A", // A simple PoS man! (Take the first word)
                is_shipping_date: true,
                is_shipping_date_today: true, //receipt had expected delivery printed
            }),
            Dialog.confirm("Continue with limited functionality"),
            FeedbackScreen.clickNextOrder(),

            // send email in receipt screen
            ProductScreen.addOrderline("Desk Pad", "6", "5", "30.0"),
            ProductScreen.addOrderline("Whiteboard Pen", "6", "6", "36.0"),
            ProductScreen.addOrderline("Monitor Stand", "6", "1", "6.0"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.enterPaymentLineAmount("Cash", "70", true, { remaining: "2.0" }),
            PaymentScreen.clickNumpad("0"),
            PaymentScreen.fillPaymentLineAmountMobile("Cash", "700"),
            PaymentScreen.changeIs("628.0"),
            OfflineUtil.setOnlineMode(),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
            StockFeedbackScreen.checkTicketData({
                total_amount: "72.00",
            }),
            FeedbackScreen.sendEmail("test@feedbackscreen.com", true),
            OfflineUtil.setOfflineMode(),
            FeedbackScreen.clickNextOrder(),

            // order with tip
            // check if tip amount is displayed
            ProductScreen.addOrderline("Desk Pad", "6", "5"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickTipButton(),
            NumberPopup.enterValue("10"),
            NumberPopup.isShown("$ 10"),
            NumberPopup.hasTypeSelected("fixed"),
            NumberPopup.clickType("percent"),
            NumberPopup.hasTypeSelected("percent"),
            NumberPopup.isShown("10 %"),
            Dialog.confirm(),
            PaymentScreen.emptyPaymentlines("33.0"),
            PaymentScreen.clickTipButton(),
            NumberPopup.isShown("10 %"),
            NumberPopup.hasTypeSelected("percent"),
            NumberPopup.enterValue("5"),
            NumberPopup.clickType("fixed"),
            NumberPopup.hasTypeSelected("fixed"),
            NumberPopup.isShown("$ 5"),
            Dialog.confirm(),
            PaymentScreen.emptyPaymentlines("35.0"),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.tipContainerIsShown(true),
            PaymentScreen.clickTipButton(),
            NumberPopup.enterValue("0"),
            NumberPopup.clickType("fixed"),
            NumberPopup.hasTypeSelected("fixed"),
            NumberPopup.isShown("$ 0"),
            Dialog.confirm(),
            PaymentScreen.selectedPaymentlineHas("Cash", "30.0"),
            PaymentScreen.tipContainerIsShown(false),
            PaymentScreen.clickTipButton(),
            NumberPopup.enterValue("1"),
            NumberPopup.clickType("fixed"),
            NumberPopup.hasTypeSelected("fixed"),
            NumberPopup.isShown("$ 1"),
            Dialog.confirm(),
            PaymentScreen.selectedPaymentlineHas("Cash", "31.0"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
            FeedbackScreen.checkTicketData({
                total_amount: "31.00",
                orderlines: [{ name: "Desk Pad" }, { name: "Tips", amount: "1.00" }],
            }),
            FeedbackScreen.clickNextOrder(),

            // Test customer note in receipt
            ProductScreen.addOrderline("Desk Pad", "1", "5"),
            inLeftSide([
                { ...ProductScreen.clickLine("Desk Pad")[0], isActive: ["mobile"] },
                ...ProductScreen.addCustomerNote("Test customer note"),
            ]),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
            FeedbackScreen.checkTicketData({
                orderlines: [
                    {
                        name: "Desk Pad",
                        cssRules: [
                            {
                                css: ".info-list .customer-note",
                                text: "Test customer note",
                            },
                        ],
                    },
                ],
            }),
            FeedbackScreen.clickNextOrder(),

            // Test that Internal notes are not available on receipt
            ProductScreen.addOrderline("Desk Pad", "1", "5"),
            inLeftSide([
                { ...ProductScreen.clickLine("Desk Pad")[0], isActive: ["mobile"] },
                ...ProductScreen.addInternalNote("Test internal note"),
                ...ProductScreen.clickSelectedLine("Desk Pad"),
                ...ProductScreen.addInternalNote("Test internal note on order"),
                ...Order.hasInternalNote("Test internal note on order"),
            ]),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
            FeedbackScreen.checkTicketData({
                orderlines: [
                    {
                        name: "Desk Pad",
                        cssRules: [
                            {
                                css: ".info-list .o_tag_badge_text",
                                text: "Test internal note",
                                negation: true,
                            },
                        ],
                    },
                ],
                cssRules: [
                    {
                        css: ".order-container .internal-note-container span div",
                        text: "Test internal note on order",
                        negation: true,
                    },
                ],
            }),
            FeedbackScreen.clickNextOrder(),

            // Test discount and original price
            ProductScreen.addOrderline("Desk Pad", "1", "20"),
            inLeftSide([
                { ...ProductScreen.clickLine("Desk Pad")[0], isActive: ["mobile"] },
                Numpad.click("%"),
                ...ProductScreen.selectedOrderlineHasDirect("Desk Pad", "1", "20"),
                Numpad.click("5"),
                ...ProductScreen.selectedOrderlineHasDirect("Desk Pad", "1", "19.0"),
                Numpad.click("."),
            ]),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
            FeedbackScreen.checkTicketData({
                orderlines: [
                    {
                        name: "Desk Pad",
                        price_unit: "19", // use baseprice with discount
                    },
                ],
                total_amount: "19.00",
            }),
            FeedbackScreen.clickNextOrder(),
            OfflineUtil.setOnlineMode(),
        ].flat(),
});

registry.category("web_tour.tours").add("ReceiptTrackingMethodTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Product A"),
            StockProductScreen.enterLotNumber("123456789", "lot"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
            FeedbackScreen.checkTicketData({
                orderlines: [
                    { name: "Product A", cssRules: [{ css: ".lot-number", text: "123456789" }] },
                ],
            }),
        ].flat(),
});
