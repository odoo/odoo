import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("PaymentScreenTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            ProductScreen.addOrderline("Letter Tray", "10"),
            ProductScreen.clickPayButton(),
            PaymentScreen.emptyPaymentlines("52.8"),

            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.enterPaymentLineAmount("Cash", "11", true, {
                amount: "11.00",
                remaining: "41.8",
            }),
            PaymentScreen.validateButtonIsHighlighted(false),
            // remove the selected paymentline with multiple backspace presses
            PaymentScreen.clickNumpad("⌫ ⌫"),
            PaymentScreen.fillPaymentLineAmountMobile("Cash", "0"),
            PaymentScreen.selectedPaymentlineHas("Cash", "0.00"),
            PaymentScreen.clickPaymentlineDelButton("Cash", "0", true),
            PaymentScreen.emptyPaymentlines("52.8"),

            // Pay with bank, the selected line should have full amount
            PaymentScreen.clickPaymentMethod("Bank", true, { remaining: "0.0" }),
            PaymentScreen.validateButtonIsHighlighted(true),
            // remove the line using the delete button
            PaymentScreen.clickPaymentlineDelButton("Bank", "52.8"),

            // Use +10 and +50 to increment the amount of the paymentline
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickNumpad("+10"),
            PaymentScreen.fillPaymentLineAmountMobile("Cash", "10"),
            PaymentScreen.remainingIs("42.8"),
            PaymentScreen.validateButtonIsHighlighted(false),
            PaymentScreen.clickNumpad("5"),
            PaymentScreen.fillPaymentLineAmountMobile("Cash", "105"),
            PaymentScreen.changeIs("52.2"),
            PaymentScreen.validateButtonIsHighlighted(true),
            PaymentScreen.clickNumpad("+50"),
            PaymentScreen.fillPaymentLineAmountMobile("Cash", "155"),
            PaymentScreen.changeIs("102.2"),
            PaymentScreen.validateButtonIsHighlighted(true),
            PaymentScreen.clickPaymentlineDelButton("Cash", "155.0"),

            // Multiple paymentlines
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickNumpad("1"),
            PaymentScreen.fillPaymentLineAmountMobile("Cash", "1"),
            PaymentScreen.remainingIs("51.8"),
            PaymentScreen.validateButtonIsHighlighted(false),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.fillPaymentLineAmountMobile("Bank", "5"),
            PaymentScreen.clickNumpad("5"),
            PaymentScreen.remainingIs("46.8"),
            PaymentScreen.validateButtonIsHighlighted(false),
            PaymentScreen.clickPaymentMethod("Bank", true, { remaining: "0.0" }),
            PaymentScreen.validateButtonIsHighlighted(true),
        ].flat(),
});

registry.category("web_tour.tours").add("PaymentScreenTour2", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Letter Tray", "1", "10"),
            ProductScreen.clickPayButton(),

            // check that ship later button is present
            { trigger: ".payment-buttons button:contains('Ship Later')" },

            PaymentScreen.enterPaymentLineAmount("Bank", "99"),
            // trying to put 99 as an amount should throw an error. We thus confirm the dialog.
            Dialog.confirm(),
            PaymentScreen.remainingIs("0.0"),
        ].flat(),
});

registry.category("web_tour.tours").add("PaymentScreenRoundingUp", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Product Test", "1"),
            ProductScreen.clickPayButton(),

            PaymentScreen.totalIs("1.96"),
            PaymentScreen.clickPaymentMethod("Cash", true, { remaining: "0.0", amount: "2.00" }),

            Chrome.clickMenuOption("Orders"),
            Chrome.createFloatingOrder(),

            // To get negative of existing quantity just send -
            ProductScreen.addOrderline("Product Test", "-"),
            ProductScreen.clickPayButton(),

            PaymentScreen.totalIs("-1.96"),
            PaymentScreen.clickPaymentMethod("Cash", true, { remaining: "0.0", amount: "-2.00" }),
        ].flat(),
});

registry.category("web_tour.tours").add("PaymentScreenRoundingDown", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Product Test", "1"),
            ProductScreen.clickPayButton(),

            PaymentScreen.totalIs("1.98"),
            PaymentScreen.clickPaymentMethod("Cash", true, { remaining: "0.0", amount: "1.95" }),

            Chrome.clickMenuOption("Orders"),
            Chrome.createFloatingOrder(),

            // To get negative of existing quantity just send -
            ProductScreen.addOrderline("Product Test", "-"),
            ProductScreen.clickPayButton(),

            PaymentScreen.totalIs("-1.98"),
            PaymentScreen.clickPaymentMethod("Cash", true, { remaining: "0.0", amount: "-1.95" }),
        ].flat(),
});

registry.category("web_tour.tours").add("PaymentScreenRoundingHalfUp", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Product Test 1.20", "1"),
            ProductScreen.clickPayButton(),

            PaymentScreen.totalIs("1.20"),
            PaymentScreen.clickPaymentMethod("Cash", true, { remaining: "0.0", amount: "1.00" }),

            Chrome.clickMenuOption("Orders"),
            Chrome.createFloatingOrder(),

            ProductScreen.addOrderline("Product Test 1.25", "1"),
            ProductScreen.clickPayButton(),

            PaymentScreen.totalIs("1.25"),
            PaymentScreen.clickPaymentMethod("Cash", true, { remaining: "0.0", amount: "1.50" }),

            Chrome.clickMenuOption("Orders"),
            Chrome.createFloatingOrder(),

            ProductScreen.addOrderline("Product Test 1.4", "1"),
            ProductScreen.clickPayButton(),

            PaymentScreen.totalIs("1.4"),
            PaymentScreen.clickPaymentMethod("Cash", true, { remaining: "0.0", amount: "1.50" }),

            Chrome.clickMenuOption("Orders"),
            Chrome.createFloatingOrder(),

            ProductScreen.addOrderline("Product Test 1.20", "1"),
            ProductScreen.clickPayButton(),

            PaymentScreen.totalIs("1.20"),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickNumpad("2"),
            PaymentScreen.fillPaymentLineAmountMobile("Cash", "2"),

            PaymentScreen.changeIs("1.0"),
        ].flat(),
});

registry.category("web_tour.tours").add("PaymentScreenTotalDueWithOverPayment", {
    steps: () =>
        [
            Chrome.startPoS(),
            ProductScreen.addOrderline("Product Test", "1"),
            ProductScreen.clickPayButton(),

            PaymentScreen.totalIs("1.98"),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.enterPaymentLineAmount("Cash", "5", true, {
                change: "3.05",
            }),
        ].flat(),
});

registry.category("web_tour.tours").add("InvoiceShipLaterAccessRight", {
    steps: () =>
        [
            Chrome.startPoS(),
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.clickHomeCategory(),
            ProductScreen.addOrderline("Whiteboard Pen", "1"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Acme Corporation"),
            ProductScreen.clickPayButton(),

            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickShipLaterButton(),
            PaymentScreen.clickValidate(),
        ].flat(),
});

registry.category("web_tour.tours").add("CashRoundingPayment", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Magnetic Board", "1"),
            ProductScreen.clickPayButton(),

            // Pay it with exact amount but with incorrect rounding so there should be an error popup.
            PaymentScreen.totalIs("1.98"),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.enterPaymentLineAmount("Cash", "1.98"),
            PaymentScreen.clickValidate(),
            Dialog.is(),
        ].flat(),
});

registry.category("web_tour.tours").add("PaymentScreenInvoiceOrder", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Product Test", "1"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner Test 1"),
            ProductScreen.clickPayButton(),

            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickInvoiceButton(),
            PaymentScreen.clickValidate(),
        ].flat(),
});
