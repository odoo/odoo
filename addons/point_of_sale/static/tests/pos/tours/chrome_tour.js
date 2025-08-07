import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as CashMoveList from "@point_of_sale/../tests/pos/tours/utils/cash_move_list_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as TicketScreen from "@point_of_sale/../tests/pos/tours/utils/ticket_screen_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Utils from "@point_of_sale/../tests/pos/tours/utils/common";
import { refresh } from "@point_of_sale/../tests/generic_helpers/utils";
import { registry } from "@web/core/registry";
import { inLeftSide } from "@point_of_sale/../tests/pos/tours/utils/common";

registry.category("web_tour.tours").add("ChromeTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            Chrome.clickMenuButton(),
            Chrome.clickMenuDropdownOption("Cash In/Out"),
            Chrome.fillTextArea(".cash-reason", "MOBT"),
            Dialog.confirm(),
            Chrome.clickMenuButton(),

            // Order 1 is at Product Screen
            ProductScreen.addOrderline("Desk Pad", "1", "2", "2.0"),
            Chrome.clickOrders(),
            TicketScreen.checkStatus("001", "Ongoing"),

            // Order 2 is at Payment Screen
            Chrome.createFloatingOrder(),
            ProductScreen.addOrderline("Monitor Stand", "3", "4", "12.0"),
            ProductScreen.clickPayButton(),
            PaymentScreen.isShown(),
            Chrome.clickOrders(),
            TicketScreen.checkStatus("002", "Payment"),

            // Order 3 is at Receipt Screen
            Chrome.createFloatingOrder(),
            ProductScreen.addOrderline("Whiteboard Pen", "5", "6", "30.0"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank", true, { remaining: "0.0" }),
            PaymentScreen.validateButtonIsHighlighted(true),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            Chrome.clickOrders(),
            TicketScreen.checkStatus("003", "Receipt"),

            // Select order 1, should be at Product Screen
            TicketScreen.selectOrder("001"),
            TicketScreen.loadSelectedOrder(),
            ProductScreen.productIsDisplayed("Desk Pad"),
            inLeftSide([
                ...ProductScreen.clickLine("Desk Pad"),
                ...ProductScreen.selectedOrderlineHasDirect("Desk Pad", "1", "2.0"),
            ]),

            // Select order 2, should be at Payment Screen
            Chrome.clickOrders(),
            TicketScreen.selectOrder("002"),
            TicketScreen.loadSelectedOrder(),
            PaymentScreen.emptyPaymentlines("12.0"),
            PaymentScreen.validateButtonIsHighlighted(false),

            // Select order 3, should be at Receipt Screen
            Chrome.clickOrders(),
            TicketScreen.selectOrder("003"),
            TicketScreen.loadSelectedOrder(),
            ReceiptScreen.totalAmountContains("30.0"),

            // Pay order 1, with change
            Chrome.clickOrders(),
            TicketScreen.selectOrder("001"),
            TicketScreen.loadSelectedOrder(),
            ProductScreen.isShown(),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.enterPaymentLineAmount("Cash", "20", true, { change: "18.0" }),
            PaymentScreen.validateButtonIsHighlighted(true),
            PaymentScreen.clickValidate(),
            ReceiptScreen.totalAmountContains("2.0"),

            // Order 1 now should have Receipt status
            Chrome.clickOrders(),
            TicketScreen.checkStatus("001", "Receipt"),

            // Select order 3, should still be at Receipt Screen
            // and the total amount doesn't change.
            TicketScreen.selectOrder("003"),
            TicketScreen.loadSelectedOrder(),
            ReceiptScreen.totalAmountContains("30.0"),

            // click next screen on order 3
            // then delete the new empty order
            ReceiptScreen.clickNextOrder(),
            ProductScreen.orderIsEmpty(),
            Chrome.clickOrders(),
            TicketScreen.deleteOrder("004"),

            // After deleting order 1 above, order 2 became
            // the 1st-row order and it has payment status
            TicketScreen.nthRowContains(1, "Payment"),
            TicketScreen.deleteOrder("002"),
            Dialog.confirm(),
            Chrome.clickRegister(),

            // Invoice an order
            ProductScreen.addOrderline("Whiteboard Pen", "5", "6"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner Test 1"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickInvoiceButton(),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            { trigger: ".receipt-screen .pos-config-name:contains(Shop)" },

            // Cancelling a floating order should remove it from the floating orders list.
            ReceiptScreen.clickNextOrder(),
            Chrome.hasFloatingOrder("006"),
            ProductScreen.clickReview(),
            ProductScreen.clickControlButton("Cancel Order"),
            Chrome.noFloatingOrder("006"),
        ].flat(),
});

registry.category("web_tour.tours").add("OrderModificationAfterValidationError", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Test Product", true, "1"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank", true, { remaining: "0.0" }),
            PaymentScreen.clickValidate(),

            // Dialog showing the error
            Dialog.confirm(),

            PaymentScreen.clickBack(),
            { ...ProductScreen.back(), isActive: ["mobile"] },
            ProductScreen.isShown(),

            // Allow order changes after the error
            ProductScreen.clickDisplayedProduct("Test Product", true, "2"),
        ].flat(),
});

registry.category("web_tour.tours").add("test_tracking_number_closing_session", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Desk Organizer", true, "1.0"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.clickNextOrder(),
            ProductScreen.isShown(),
            Chrome.clickMenuOption("Close Register"),
            {
                content: `Select button close register`,
                trigger: `button:contains(close register)`,
                run: "click",
                expectUnloadPage: true,
            },
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Desk Pad", true, "1.0"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.enterPaymentLineAmount("Bank", "20"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            ReceiptScreen.clickNextOrder(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_reload_page_before_payment_with_customer_account", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Desk Organizer", true, "1.0"),
            refresh(),
            ProductScreen.productIsDisplayed("Desk Organizer"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner Test 1"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Customer Account"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.clickNextOrder(),
            ProductScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_cash_in_out", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            Chrome.freezeDateTime(1749965940000),
            Chrome.doCashMove("10", "MOBT in"),
            Chrome.doCashMove("5", "MOBT out"),
            Chrome.clickMenuOption("Close Register"),
            Utils.selectButton("Cash In/Out"),
            Utils.selectButton("Details"),
            CashMoveList.checkNumberOfRows(2),
            CashMoveList.checkCashMoveShown("10"),
            CashMoveList.checkCashMoveShown("5"),
            CashMoveList.checkCashMoveDateTime(),
            CashMoveList.deleteCashMove("10"),
            CashMoveList.checkNumberOfRows(1),
            CashMoveList.checkCashMoveShown("5"),
        ].flat(),
});

registry.category("web_tour.tours").add("test_zero_decimal_places_currency", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Test Product", true, "1.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.receiptIsThere(),
            ReceiptScreen.totalAmountContains("100"),
        ].flat(),
});
