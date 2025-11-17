import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as FeedbackScreen from "@point_of_sale/../tests/pos/tours/utils/feedback_screen_util";
import * as TipScreen from "@point_of_sale/../tests/pos/tours/utils/tip_screen_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as NumberPopup from "@point_of_sale/../tests/generic_helpers/number_popup_util";

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("PosTipAfterPaymentTour", {
    steps: () =>
        [
            // Open PoS
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // Bank --> Open TipScren (15%)
            ProductScreen.addOrderline("Desk Pad", "1", "2", "2.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            TipScreen.isShown(),
            TipScreen.totalAmountIs("2.00"),
            TipScreen.percentAmountIs("15%", "0.30"),
            TipScreen.percentAmountIs("20%", "0.40"),
            TipScreen.percentAmountIs("25%", "0.50"),
            TipScreen.clickPercentTip("15%"),
            TipScreen.inputAmountIs("0.30"),
            TipScreen.clickSettle(),
            FeedbackScreen.checkTicketData({
                total_amount: "2.30",
                payment_lines: [{ name: "Bank", amount: "2.00" }],
                orderlines: [
                    { name: "Desk Pad", quantity: "1", price_unit: "2.00", line_price: "2.00" },
                    { name: "Tips", quantity: "1", price_unit: "0.30", line_price: "0.30" },
                ],
            }),
            FeedbackScreen.clickNextOrder(),

            // Bank --> Open TipScren (20%)
            ProductScreen.addOrderline("Desk Pad", "2", "2", "4.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            TipScreen.isShown(),
            TipScreen.totalAmountIs("4.00"),
            TipScreen.percentAmountIs("15%", "0.60"),
            TipScreen.percentAmountIs("20%", "0.80"),
            TipScreen.percentAmountIs("25%", "1.00"),
            TipScreen.clickPercentTip("20%"),
            TipScreen.inputAmountIs("0.80"),
            TipScreen.clickSettle(),
            FeedbackScreen.checkTicketData({
                total_amount: "4.80",
                payment_lines: [{ name: "Bank", amount: "4.00" }],
                orderlines: [
                    { name: "Desk Pad", quantity: "2", price_unit: "2.00", line_price: "4.00" },
                    { name: "Tips", quantity: "1", price_unit: "0.80", line_price: "0.80" },
                ],
            }),
            FeedbackScreen.clickNextOrder(),

            // Bank --> Open TipScren (25%)
            ProductScreen.addOrderline("Desk Pad", "3", "2", "6.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            TipScreen.isShown(),
            TipScreen.totalAmountIs("6.00"),
            TipScreen.percentAmountIs("15%", "0.90"),
            TipScreen.percentAmountIs("20%", "1.20"),
            TipScreen.percentAmountIs("25%", "1.50"),
            TipScreen.clickPercentTip("25%"),
            TipScreen.inputAmountIs("1.50"),
            TipScreen.clickSettle(),
            FeedbackScreen.checkTicketData({
                total_amount: "7.50",
                payment_lines: [{ name: "Bank", amount: "6.00" }],
                orderlines: [
                    { name: "Desk Pad", quantity: "3", price_unit: "2.00", line_price: "6.00" },
                    { name: "Tips", quantity: "1", price_unit: "1.50", line_price: "1.50" },
                ],
            }),
            FeedbackScreen.clickNextOrder(),

            // Bank --> Open TipScren (25%)
            ProductScreen.addOrderline("Desk Pad", "4", "2", "8.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            TipScreen.isShown(),
            TipScreen.totalAmountIs("8.00"),
            TipScreen.percentAmountIs("15%", "1.20"),
            TipScreen.percentAmountIs("20%", "1.60"),
            TipScreen.percentAmountIs("25%", "2.00"),
            TipScreen.clickPercentTip("25%"),
            TipScreen.inputAmountIs("2.00"),
            TipScreen.clickSettle(),
            FeedbackScreen.checkTicketData({
                total_amount: "10.00",
                payment_lines: [{ name: "Bank", amount: "8.00" }],
                orderlines: [
                    { name: "Desk Pad", quantity: "4", price_unit: "2.00", line_price: "8.00" },
                    { name: "Tips", quantity: "1", price_unit: "2.00", line_price: "2.00" },
                ],
            }),
            FeedbackScreen.clickNextOrder(),

            // Bank --> Open TipScren (No Tip)
            ProductScreen.addOrderline("Desk Pad", "5", "2", "10.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            TipScreen.isShown(),
            TipScreen.totalAmountIs("10.00"),
            TipScreen.percentAmountIs("15%", "1.50"),
            TipScreen.percentAmountIs("20%", "2.00"),
            TipScreen.percentAmountIs("25%", "2.50"),
            TipScreen.clickNoTip(),
            TipScreen.inputAmountIs("0"),
            TipScreen.clickSettle(),
            FeedbackScreen.checkTicketData({
                total_amount: "10.00",
                payment_lines: [{ name: "Bank", amount: "10.00" }],
                orderlines: [
                    { name: "Desk Pad", quantity: "5", price_unit: "2.00", line_price: "10.00" },
                ],
            }),
            FeedbackScreen.clickNextOrder(),

            // Bank --> Open TipScren (Custom Tip)
            ProductScreen.addOrderline("Desk Pad", "6", "2", "12.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            TipScreen.isShown(),
            TipScreen.totalAmountIs("12.00"),
            TipScreen.percentAmountIs("15%", "1.80"),
            TipScreen.percentAmountIs("20%", "2.40"),
            TipScreen.percentAmountIs("25%", "3.00"),
            TipScreen.setCustomTip("1.00"),
            TipScreen.inputAmountIs("1.00"),
            TipScreen.clickSettle(),
            FeedbackScreen.checkTicketData({
                total_amount: "13.00",
                payment_lines: [{ name: "Bank", amount: "12.00" }],
                orderlines: [
                    { name: "Desk Pad", quantity: "6", price_unit: "2.00", line_price: "12.00" },
                    { name: "Tips", quantity: "1", price_unit: "1.00", line_price: "1.00" },
                ],
            }),
            FeedbackScreen.clickNextOrder(),

            // Bank --> Open TipScren (Directly Settle)
            ProductScreen.addOrderline("Desk Pad", "7", "2", "14.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            TipScreen.isShown(),
            TipScreen.totalAmountIs("14.00"),
            TipScreen.percentAmountIs("15%", "2.10"),
            TipScreen.percentAmountIs("20%", "2.80"),
            TipScreen.percentAmountIs("25%", "3.50"),
            TipScreen.inputAmountIs(""),
            TipScreen.clickSettle(),
            FeedbackScreen.checkTicketData({
                total_amount: "14.00",
                payment_lines: [{ name: "Bank", amount: "14.00" }],
                orderlines: [
                    { name: "Desk Pad", quantity: "7", price_unit: "2.00", line_price: "14.00" },
                ],
            }),
            FeedbackScreen.clickNextOrder(),

            // Cash --> Do not open TipScreen
            ProductScreen.addOrderline("Desk Pad", "8", "2", "16.0"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
            FeedbackScreen.checkTicketData({
                total_amount: "16.00",
                payment_lines: [{ name: "Cash", amount: "16.00" }],
                orderlines: [
                    { name: "Desk Pad", quantity: "8", price_unit: "2.00", line_price: "16.00" },
                ],
            }),
            FeedbackScreen.clickNextOrder(),

            // Bank + Already tipped --> Open ReceiptScreen
            ProductScreen.addOrderline("Desk Pad", "4", "25", "100.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickTipButton(),
            NumberPopup.enterValue("10"),
            NumberPopup.isShown("$ 10"),
            Dialog.confirm(),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
            FeedbackScreen.checkTicketData({
                total_amount: "110.00",
                payment_lines: [{ name: "Bank", amount: "110.00" }],
                orderlines: [
                    { name: "Desk Pad", quantity: "4", price_unit: "25.00", line_price: "100.00" },
                    { name: "Tips", quantity: "1", price_unit: "10.00", line_price: "10.00" },
                ],
            }),
            FeedbackScreen.clickNextOrder(),

            // Bank + Delete Tip --> Open TipScreen --> No Tip
            ProductScreen.addOrderline("Desk Pad", "4", "25", "100.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickTipButton(),
            NumberPopup.enterValue("25"),
            NumberPopup.isShown("$ 25"),
            NumberPopup.hasTypeSelected("fixed"),
            NumberPopup.clickType("percent"),
            NumberPopup.hasTypeSelected("percent"),
            NumberPopup.isShown("25 %"),
            Dialog.confirm(),
            PaymentScreen.clickTipButton(),
            NumberPopup.enterValue("⌫"),
            NumberPopup.isShown("%"),
            Dialog.confirm(),
            PaymentScreen.clickValidate(),
            TipScreen.isShown(),
            TipScreen.totalAmountIs("100.00"),
            TipScreen.percentAmountIs("15%", "15.00"),
            TipScreen.percentAmountIs("20%", "20.00"),
            TipScreen.percentAmountIs("25%", "25.00"),
            TipScreen.inputAmountIs(""),
            TipScreen.clickSettle(),
            FeedbackScreen.isShown(),
            FeedbackScreen.checkTicketData({
                total_amount: "100.00",
                payment_lines: [{ name: "Bank", amount: "100.00" }],
                orderlines: [
                    { name: "Desk Pad", quantity: "4", price_unit: "25.00", line_price: "100.00" },
                ],
            }),
            FeedbackScreen.clickNextOrder(),

            // Bank + 0 tip --> Open TipScreen --> No Tip
            ProductScreen.addOrderline("Desk Pad", "4", "25", "100.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickTipButton(),
            NumberPopup.enterValue("0"),
            NumberPopup.isShown("$ 0"),
            Dialog.confirm(),
            PaymentScreen.clickValidate(),
            TipScreen.isShown(),
            TipScreen.totalAmountIs("100.00"),
            TipScreen.percentAmountIs("15%", "15.00"),
            TipScreen.percentAmountIs("20%", "20.00"),
            TipScreen.percentAmountIs("25%", "25.00"),
            TipScreen.inputAmountIs(""),
            TipScreen.clickSettle(),
            FeedbackScreen.isShown(),
            FeedbackScreen.checkTicketData({
                total_amount: "100.00",
                payment_lines: [{ name: "Bank", amount: "100.00" }],
                orderlines: [
                    { name: "Desk Pad", quantity: "4", price_unit: "25.00", line_price: "100.00" },
                ],
            }),
            FeedbackScreen.clickNextOrder(),
        ].flat(),
});
