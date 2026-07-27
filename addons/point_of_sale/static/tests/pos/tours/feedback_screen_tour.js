/* global posmodel */

import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as FeedbackScreen from "@point_of_sale/../tests/pos/tours/utils/feedback_screen_util";
import * as NumberPopup from "@point_of_sale/../tests/generic_helpers/number_popup_util";
import * as Numpad from "@point_of_sale/../tests/generic_helpers/numpad_util";
import * as OfflineUtil from "@point_of_sale/../tests/generic_helpers/offline_util";
import { registry } from "@web/core/registry";
import { inLeftSide } from "@point_of_sale/../tests/pos/tours/utils/common";

registry.category("web_tour.tours").add("FeedbackScreenTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            OfflineUtil.setOfflineMode(),
            ProductScreen.addOrderline("Letter Tray", "10", "5"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("APartner Full"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.validateButtonIsHighlighted(true),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
            FeedbackScreen.checkTicketData({
                total_amount: "55.00", // letter tray has 10% tax (search SRC)
                cashier_name: "A", // A simple PoS man! (Take the first word)
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
            FeedbackScreen.checkTicketData({
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
            {
                content: "When the tip will be removed, it requires delay",
                trigger: `.modal .value:contains("0.00")`,
                async run() {
                    await new Promise((r) => setTimeout(r, 500));
                },
            },
            Dialog.confirm(),
            PaymentScreen.selectedPaymentlineHas("Cash", "30.0"),
            PaymentScreen.tipContainerIsShown(false),
            PaymentScreen.clickTipButton(),
            NumberPopup.enterValue("1"),
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
                                css: ".lines .line-note",
                                text: "Test customer note",
                            },
                        ],
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

registry.category("web_tour.tours").add("OrderPaidInCash", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Desk Pad", "5", "5"),
            inLeftSide(ProductScreen.orderLineHas("Desk Pad", "5")),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.validateButtonIsHighlighted(true),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
            FeedbackScreen.clickNextOrder(),
            ProductScreen.isShown(),
            // Close the session
            Chrome.clickMenuOption("Close Register"),
            ProductScreen.closeWithCashAmount("25"),
            ProductScreen.cashDifferenceIs("0.00"),
            {
                trigger: ".modal .modal-footer .btn:contains(close register)",
                run: "click",
                expectUnloadPage: true,
            },
            {
                trigger: "button:contains(backend)",
                run: "click",
                expectUnloadPage: true,
            },
            {
                trigger: "body",
                expectUnloadPage: true,
            },
        ].flat(),
});

registry.category("web_tour.tours").add("test_auto_validate_force_done", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Whiteboard Pen", "1"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            {
                trigger: "body",
                run: () => {
                    posmodel.getOrder().payment_ids[0].setPaymentStatus("force_done");
                },
            },
            PaymentScreen.clickForceDoneButton(),
            FeedbackScreen.isShown(),
        ].flat(),
});
