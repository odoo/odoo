import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import { registry } from "@web/core/registry";
import * as OfflineUtil from "@point_of_sale/../tests/generic_helpers/offline_util";
import * as TicketScreen from "@point_of_sale/../tests/pos/tours/utils/ticket_screen_util";
import * as Order from "@point_of_sale/../tests/generic_helpers/order_widget_util";
import * as Numpad from "@point_of_sale/../tests/generic_helpers/numpad_util";
import { inLeftSide } from "./utils/common";

registry.category("web_tour.tours").add("PaymentScreenTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            OfflineUtil.setOfflineMode(),
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
            PaymentScreen.clickNumpad("⌫"),
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
            OfflineUtil.setOnlineMode(),
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
            PaymentScreen.clickValidate(),

            Chrome.clickOrders(),
            TicketScreen.selectFilter("Paid"),
            TicketScreen.selectOrder("001"),
            inLeftSide([
                ...Order.hasLine({ productName: "Product Test", withClass: ".selected" }),
                Numpad.click("1"),
            ]),
            TicketScreen.confirmRefund(),

            // To get negative of existing quantity just send -
            PaymentScreen.isShown(),
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
            PaymentScreen.clickValidate(),

            Chrome.clickOrders(),
            TicketScreen.selectFilter("Paid"),
            TicketScreen.selectOrder("001"),
            inLeftSide([
                ...Order.hasLine({ productName: "Product Test", withClass: ".selected" }),
                Numpad.click("1"),
            ]),
            TicketScreen.confirmRefund(),

            // To get negative of existing quantity just send -
            PaymentScreen.isShown(),
            PaymentScreen.totalIs("-1.98"),
            PaymentScreen.clickPaymentMethod("Cash", true, { remaining: "0.0", amount: "-1.95" }),
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
                change: "3",
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
            ProductScreen.clickCustomer("Deco Addict"),
            ProductScreen.clickPayButton(),

            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickShipLaterButton(),
            PaymentScreen.clickValidate(),
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

registry.category("web_tour.tours").add("test_pos_large_amount_confirmation_dialog", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Overpay Test Product"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.enterPaymentLineAmount("Cash", "1500"),
            PaymentScreen.clickValidate(),
            {
                trigger: ".modal .modal-footer .btn-primary",
                run: "click",
            },
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_add_money_button_with_different_decimal_separator", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Ouvrir la caisse"),
            ProductScreen.addOrderline("Whiteboard Pen", "1"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickNumpad("+50"),
            PaymentScreen.fillPaymentLineAmountMobile("Bank", "53,20"),
            PaymentScreen.changeIs("50"),
        ].flat(),
});
