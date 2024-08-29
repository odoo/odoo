import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/utils/receipt_screen_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as TicketScreen from "@point_of_sale/../tests/tours/utils/ticket_screen_util";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("ChromeTour", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),

            Chrome.clickMenuButton(),
            Chrome.clickMenuDropdownOption("Cash In/Out"),
            Dialog.confirm(),
            Chrome.clickMenuButton(),

            // Order 1 is at Product Screen
            ProductScreen.addOrderline("Desk Pad", "1", "2", "2.0"),

            // Order 2 is at Payment Screen
            Chrome.newFloatingOrder(),
            ProductScreen.addOrderline("Monitor Stand", "3", "4", "12.0"),
            ProductScreen.clickPayButton(),
            PaymentScreen.isShown(),

            // Order 3 is at Receipt Screen
            Chrome.newFloatingOrder(),
            ProductScreen.addOrderline("Whiteboard Pen", "5", "6", "30.0"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank", true, { remaining: "0.0" }),
            PaymentScreen.validateButtonIsHighlighted(true),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            // Order 3 should not appear in the floating order list
            Chrome.floatingOrderDoesNotExist("03"),

            // Select order 1, should be at Product Screen
            Chrome.clickFloatingOrder("01"),
            ProductScreen.productIsDisplayed("Desk Pad"),
            ProductScreen.selectedOrderlineHas("Desk Pad", "1.0", "2.0"),

            // Select order 2, should be at Payment Screen
            Chrome.clickFloatingOrder("02"),
            PaymentScreen.emptyPaymentlines("12.0"),
            PaymentScreen.validateButtonIsHighlighted(false),

            // Pay order 1, with change
            Chrome.clickFloatingOrder("01"),
            ProductScreen.isShown(),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.enterPaymentLineAmount("Cash", "20", true, { change: "18.0" }),
            PaymentScreen.validateButtonIsHighlighted(true),
            PaymentScreen.clickValidate(),
            ReceiptScreen.totalAmountContains("2.0"),

            // Order 1 now should have Receipt status
            Chrome.clickMenuOption("Orders"),
            TicketScreen.checkStatus("-0001", "Paid"),
            TicketScreen.checkStatus("-0003", "Paid"),

            Chrome.newFloatingOrder(),
            // Invoice an order
            ProductScreen.addOrderline("Whiteboard Pen", "5", "6"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner Test 1"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickInvoiceButton(),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("OrderModificationAfterValidationError", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),
            ProductScreen.clickDisplayedProduct("Test Product", true, "1.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank", true, { remaining: "0.0" }),
            PaymentScreen.clickValidate(),

            // Dialog showing the error
            Dialog.confirm(),

            PaymentScreen.clickBack(),
            { ...ProductScreen.back(), isActive: ["mobile"] },
            ProductScreen.isShown(),

            // Allow order changes after the error
            ProductScreen.clickDisplayedProduct("Test Product", true, "2.00"),
        ].flat(),
});
