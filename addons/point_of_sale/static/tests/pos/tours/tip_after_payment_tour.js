import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";
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
            ReceiptScreen.totalAmountWithTipContains("2.00", "0.30", {
                tip15: "$ 0.30",
                tip20: "$ 0.40",
                tip25: "$ 0.50",
            }),
            ReceiptScreen.clickNextOrder(),

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
            ReceiptScreen.totalAmountWithTipContains("4.00", "0.80", {
                tip15: "$ 0.60",
                tip20: "$ 0.80",
                tip25: "$ 1.00",
            }),
            ReceiptScreen.clickNextOrder(),

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
            ReceiptScreen.totalAmountWithTipContains("6.00", "1.50", {
                tip15: "$ 0.90",
                tip20: "$ 1.20",
                tip25: "$ 1.50",
            }),
            ReceiptScreen.clickNextOrder(),

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
            ReceiptScreen.totalAmountWithTipContains("8.00", "2.00", {
                tip15: "$ 1.20",
                tip20: "$ 1.60",
                tip25: "$ 2.00",
            }),
            ReceiptScreen.clickNextOrder(),

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
            ReceiptScreen.totalAmountWithTipContains("10.00", null, {
                tip15: "$ 1.50",
                tip20: "$ 2.00",
                tip25: "$ 2.50",
            }),
            ReceiptScreen.clickNextOrder(),

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
            ReceiptScreen.totalAmountWithTipContains("12.00", "1.00", {
                tip15: "$ 1.80",
                tip20: "$ 2.40",
                tip25: "$ 3.00",
            }),
            ReceiptScreen.clickNextOrder(),

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
            ReceiptScreen.totalAmountWithTipContains("14.00", null, {
                tip15: "$ 2.10",
                tip20: "$ 2.80",
                tip25: "$ 3.50",
            }),
            ReceiptScreen.clickNextOrder(),

            // Cash --> Do not open TipScreen
            ProductScreen.addOrderline("Desk Pad", "8", "2", "16.0"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            ReceiptScreen.totalAmountWithTipContains("16.00", null, {
                tip15: "$ 2.40",
                tip20: "$ 3.20",
                tip25: "$ 4.00",
            }),
            ReceiptScreen.clickNextOrder(),

            // Bank + Already tipped --> Open ReceiptScreen
            ProductScreen.addOrderline("Desk Pad", "4", "25", "100.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickTipButton(),
            NumberPopup.enterValue("10"),
            NumberPopup.isShown("$ 10"),
            Dialog.confirm(),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            ReceiptScreen.totalAmountWithTipContains("100.00", "10.00", {
                tip15: "$ 15.00",
                tip20: "$ 20.00",
                tip25: "$ 25.00",
            }),
            ReceiptScreen.clickNextOrder(),

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
            ReceiptScreen.totalAmountWithTipContains("100.00", null, {
                tip15: "$ 15.00",
                tip20: "$ 20.00",
                tip25: "$ 25.00",
            }),
            ReceiptScreen.clickNextOrder(),

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
            ReceiptScreen.totalAmountWithTipContains("100.00", null, {
                tip15: "$ 15.00",
                tip20: "$ 20.00",
                tip25: "$ 25.00",
            }),
            ReceiptScreen.clickNextOrder(),
        ].flat(),
});
