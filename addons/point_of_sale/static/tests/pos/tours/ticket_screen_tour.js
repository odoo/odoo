import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as Numpad from "@point_of_sale/../tests/generic_helpers/numpad_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as PartnerList from "@point_of_sale/../tests/pos/tours/utils/partner_list_util";
import * as TicketScreen from "@point_of_sale/../tests/pos/tours/utils/ticket_screen_util";
import * as Order from "@point_of_sale/../tests/generic_helpers/order_widget_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import { inLeftSide } from "@point_of_sale/../tests/pos/tours/utils/common";
import { registry } from "@web/core/registry";
import * as OfflineUtil from "@point_of_sale/../tests/generic_helpers/offline_util";

registry.category("web_tour.tours").add("TicketScreenTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            OfflineUtil.setOfflineMode(),
            Chrome.clickOrders(),
            Dialog.confirm("Continue with limited functionality"),
            OfflineUtil.setOnlineMode(),
            Chrome.createFloatingOrder(),
            ProductScreen.addOrderline("Desk Pad", "1", "3"),
            Chrome.clickOrders(),
            TicketScreen.deleteOrder("002"),
            Dialog.confirm(),
            TicketScreen.nthRowContains(1, "001"),
            TicketScreen.nthRowIsHighlighted(1),
            Chrome.clickRegister(),
            ProductScreen.orderIsEmpty(),
            ProductScreen.addOrderline("Desk Pad", "1", "2"),
            Chrome.clickOrders(),
            TicketScreen.deleteOrder("001"),
            Dialog.confirm(),
            TicketScreen.nthRowContains(1, "001"),
            TicketScreen.nthRowIsHighlighted(1),
            Chrome.clickRegister(),
            ProductScreen.addOrderline("Desk Pad", "1", "2"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner Test 1"),
            Chrome.clickOrders(),
            TicketScreen.nthRowContains(1, "Partner Test 1", false),
            Chrome.createFloatingOrder(),
            ProductScreen.addOrderline("Desk Pad", "1", "3"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner Test 2"),
            ProductScreen.clickPayButton(),
            PaymentScreen.isShown(),
            Chrome.clickOrders(),
            TicketScreen.nthRowContains(1, "Partner Test 2", false),
            Chrome.createFloatingOrder(),
            ProductScreen.addOrderline("Desk Pad", "2", "4"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            Chrome.clickOrders(),
            TicketScreen.nthRowContains(3, "Receipt"),
            TicketScreen.selectFilter("Receipt"),
            TicketScreen.nthRowContains(1, "Receipt"),
            TicketScreen.selectFilter("Payment"),
            TicketScreen.nthRowContains(1, "Payment"),
            TicketScreen.selectFilter("Ongoing"),
            TicketScreen.nthRowContains(1, "Ongoing"),
            TicketScreen.selectFilter("Active"),
            TicketScreen.nthRowContains(3, "Receipt"),
            TicketScreen.search("Receipt Number", "-00003"),
            TicketScreen.nthRowContains(1, "Receipt"),
            TicketScreen.search("Customer", "Partner Test 1"),
            TicketScreen.nthRowContains(1, "Partner Test 1", false),
            TicketScreen.search("Customer", "Partner Test 2"),
            TicketScreen.nthRowContains(1, "Partner Test 2", false),
            // Close the TicketScreen to see the current order which is in ReceiptScreen.
            // This is just to remove the search string in the search bar.
            Chrome.clickRegister(),
            ReceiptScreen.isShown(),
            // Open again the TicketScreen to check the Paid filter.
            Chrome.clickOrders(),
            TicketScreen.selectFilter("Paid"),
            TicketScreen.nthRowContains(1, "003"),
            TicketScreen.selectOrder("003"),
            // Pay the order that was in PaymentScreen.
            TicketScreen.selectFilter("Payment"),
            TicketScreen.selectOrder("002"),
            TicketScreen.loadSelectedOrder(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            ReceiptScreen.clickNextOrder(),
            ProductScreen.isShown(),
            // Check that the Paid filter will show the 2 synced orders.
            Chrome.clickOrders(),
            TicketScreen.selectFilter("Paid"),
            TicketScreen.nthRowContains(1, "Partner Test 2", false),
            TicketScreen.nthRowContains(2, "003"),
            // Invoice order
            TicketScreen.selectOrder("003"),
            inLeftSide(Order.hasLine()),
            TicketScreen.clickControlButton("Invoice"),
            Dialog.confirm(),
            PartnerList.clickPartner("Partner Test 3"),
            TicketScreen.invoicePrinted(),
            TicketScreen.back(),
            // When going back, the ticket screen should be in its previous state.
            TicketScreen.filterIs("Paid"),
            // Test refund //
            Chrome.clickRegister(),
            ProductScreen.isShown(),
            ProductScreen.orderIsEmpty(),
            ...ProductScreen.clickRefund(),
            //Filter should be automatically 'Paid'.
            TicketScreen.filterIs("Paid"),
            TicketScreen.selectOrder("003"),
            inLeftSide([
                ...Order.hasLine({ productName: "Desk Pad", withClass: ".selected" }),
                Numpad.click("3"),
                Dialog.confirm(),
            ]),
            Chrome.clickRegister(),
            { ...ProductScreen.back(), isActive: ["mobile"] },
            ProductScreen.isShown(),
            ProductScreen.orderIsEmpty(),
            ...ProductScreen.clickRefund(),
            TicketScreen.selectOrder("003"),
            inLeftSide(Order.hasLine({ productName: "Desk Pad", withClass: ".selected" })),
            ProductScreen.clickNumpad("1"),
            TicketScreen.toRefundTextContains("To Refund: 1"),
            TicketScreen.confirmRefund(),
            PaymentScreen.isShown(),
            PaymentScreen.clickBack(),
            { ...ProductScreen.back(), isActive: ["mobile"] },
            ProductScreen.isShown(),
            inLeftSide([
                ...ProductScreen.clickLine("Desk Pad"),
                ...ProductScreen.selectedOrderlineHasDirect("Desk Pad", "-1"),
                // Try changing the refund line's qty, price, discount but altering of refund line not allowed.
                // Error popup should show.
                Numpad.click("2"),
                Dialog.confirm(),
                ...["Price", "2"].map(Numpad.click),
                Dialog.confirm(),
                ...["%", "5"].map(Numpad.click),
                Dialog.confirm(),
            ]),
            // Check if the amount being refunded changed to 2.
            ...ProductScreen.clickRefund(),
            TicketScreen.selectOrder("003"),
            TicketScreen.toRefundTextContains("Refunding 1.00"),
            Chrome.clickRegister(),
            { ...ProductScreen.back(), isActive: ["mobile"] },
            // Pay the refund order.
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            ReceiptScreen.clickNextOrder(),
            // Check refunded quantity.
            ...ProductScreen.clickRefund(),
            TicketScreen.selectOrder("003"),
            TicketScreen.refundedNoteContains("1.00 Refunded"),
        ].flat(),
});

registry.category("web_tour.tours").add("FiscalPositionNoTaxRefund", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Product Test"),
            ProductScreen.totalAmountIs("100.00"),
            ProductScreen.clickFiscalPosition("No Tax"),
            ProductScreen.totalAmountIs("100.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank", true, { remaining: "0.00" }),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            ReceiptScreen.clickNextOrder(),
            ...ProductScreen.clickRefund(),
            TicketScreen.selectOrder("001"),
            ProductScreen.clickNumpad("1"),
            TicketScreen.confirmRefund(),
            PaymentScreen.isShown(),
            PaymentScreen.clickBack(),
            ProductScreen.isShown(),
            { ...ProductScreen.back(), isActive: ["mobile"] },
            ProductScreen.totalAmountIs("100.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("LotRefundTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            Chrome.clickOrders(),
            Chrome.clickOnScanButton(),
            TicketScreen.checkCameraIsOpen(),
            Chrome.clickOnScanButton(),
            Chrome.clickRegister(),
            ProductScreen.clickDisplayedProduct("Product A"),
            ProductScreen.enterLotNumber("123456789"),
            ProductScreen.selectedOrderlineHas("Product A", "1"),
            Chrome.clickOrders(),
            TicketScreen.selectOrder("001"),
            Chrome.clickOnScanButton(),
            TicketScreen.checkCameraIsOpen(),
            Chrome.clickOnScanButton(),
            Chrome.clickRegister(),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            ReceiptScreen.clickNextOrder(),
            ...ProductScreen.clickRefund(),
            TicketScreen.selectOrder("001"),
            ProductScreen.clickNumpad("1"),
            TicketScreen.toRefundTextContains("To Refund: 1"),
            TicketScreen.confirmRefund(),
            PaymentScreen.isShown(),
            PaymentScreen.clickBack(),
            ProductScreen.isShown(),
            ProductScreen.clickLotIcon(),
            ProductScreen.checkFirstLotNumber("123456789"),
        ].flat(),
});

registry.category("web_tour.tours").add("RefundFewQuantities", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Sugar"),
            inLeftSide([
                ...["0", "."].map(Numpad.click),
                ...ProductScreen.selectedOrderlineHasDirect("Sugar", "0", "0.00"),
                ...["0", "2"].map(Numpad.click),
                ...ProductScreen.selectedOrderlineHasDirect("Sugar", "0.02", "0.06"),
            ]),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            ReceiptScreen.clickNextOrder(),
            ...ProductScreen.clickRefund(),
            TicketScreen.selectOrder("001"),
            ProductScreen.clickNumpad("0", "."),
            ProductScreen.clickNumpad("0", "2"),
            TicketScreen.toRefundTextContains("To Refund: 0.02"),
            TicketScreen.confirmRefund(),
            PaymentScreen.isShown(),
            PaymentScreen.clickBack(),
            ProductScreen.isShown(),
            Order.hasLine("Sugar", "-0.02", "-0.06"),
        ].flat(),
});

registry.category("web_tour.tours").add("LotTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Product A"),
            ProductScreen.enterLotNumber("1"),
            ProductScreen.selectedOrderlineHas("Product A", "1"),
            inLeftSide(
                [
                    ProductScreen.clickLotIcon(),
                    ProductScreen.deleteNthLotNumber(1),
                    ProductScreen.enterLotNumber("2", "serial", true),
                    Order.hasLine({
                        productName: "Product A",
                        quantity: 1,
                    }),
                    ProductScreen.clickLotIcon(),
                    ProductScreen.enterLotNumber("1"),
                    Order.hasLine({
                        productName: "Product A",
                        quantity: 2.0,
                    }),
                ].flat()
            ),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner Test 1"),
            ProductScreen.clickDisplayedProduct("Product A"),
            ProductScreen.enterLotNumber("3"),
            ProductScreen.selectedOrderlineHas("Product A", "3"),
            inLeftSide({
                trigger: ".info-list:contains('SN 3')",
            }),

            // Verify if the serial number can be reused for the current order
            Chrome.createFloatingOrder(),
            ProductScreen.clickDisplayedProduct("Product A"),
            ProductScreen.enterLotNumber("5"),
            ProductScreen.clickDisplayedProduct("Product A"),
            ProductScreen.enterLotNumber("3"),
            inLeftSide({
                trigger: ".info-list:not(:contains('SN 3'))",
            }),
            // Check auto assign lot number if there is only one available option
            ProductScreen.clickDisplayedProduct("Product B"),
            inLeftSide({
                trigger: ".info-list:contains('Lot Number 1001')",
            }),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            ReceiptScreen.clickNextOrder(),
            ...ProductScreen.clickRefund(),
            TicketScreen.selectOrder("002"),
            inLeftSide(
                [Numpad.click("1"), ProductScreen.clickLine("Product B"), Numpad.click("1")].flat()
            ),
            TicketScreen.confirmRefund(),
            PaymentScreen.isShown(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            ReceiptScreen.clickNextOrder(),
        ].flat(),
});

registry.category("web_tour.tours").add("OrderTimeTour", {
    steps: () => {
        const validateDateStep = {
            content: "Validate order date is Today",
            trigger: ".orders .order-row:first .fw-bolder",
            run: function ({ anchor: displayedDateElement }) {
                if (displayedDateElement.textContent.trim() !== "Today") {
                    throw new Error("Order date does not match local timezone");
                }
            },
        };

        const validateTimeStep = {
            content: "Validate order time matches local timezone",
            trigger: ".orders .order-row:first .small.text-muted",
            run: function ({ anchor: displayedTimeElement }) {
                const orderDateUTC = window.posmodel.getOrder().date_order;
                const orderDateTime = luxon.DateTime.fromSQL(orderDateUTC, {
                    zone: "UTC",
                }).toLocal();
                if (orderDateTime.toFormat("HH:mm") !== displayedTimeElement.textContent.trim()) {
                    throw new Error("Order time does not match local timezone");
                }
            },
        };

        return [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Desk Pad"),
            ProductScreen.setTimeZone("Pacific/Honolulu"),
            Chrome.clickOrders(),
            validateDateStep,
            validateTimeStep,
            ProductScreen.setTimeZone("Europe/Brussels"),
            Chrome.clickRegister(),
            Chrome.clickOrders(),
            validateDateStep,
            validateTimeStep,
        ].flat();
    },
});

registry
    .category("web_tour.tours")
    .add("test_consistent_refund_process_between_frontend_and_backend", {
        steps: () =>
            [
                Chrome.startPoS(),
                Dialog.confirm("Open Register"),
                ProductScreen.addOrderline("Desk Pad", "2", "4"),
                ProductScreen.clickPayButton(),
                PaymentScreen.clickPaymentMethod("Bank"),
                PaymentScreen.clickValidate(),
                ReceiptScreen.isShown(),
                ReceiptScreen.clickNextOrder(),
                ...ProductScreen.clickRefund(),
                TicketScreen.selectOrder("001"),
                inLeftSide(Order.hasLine({ productName: "Desk Pad", withClass: ".selected" })),
                ProductScreen.clickNumpad("1"),
                TicketScreen.toRefundTextContains("To Refund: 1"),
                TicketScreen.confirmRefund(),
                PaymentScreen.clickPaymentMethod("Bank"),
                PaymentScreen.clickValidate(),
                ReceiptScreen.isShown(),
            ].flat(),
    });

registry.category("web_tour.tours").add("test_paid_order_with_archived_product_loads", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            Chrome.clickOrders(),
            TicketScreen.selectFilter("Paid"),
            TicketScreen.nthRowContains(1, "0002"),
            TicketScreen.selectOrder("0002"),
            inLeftSide([
                ...Order.hasLine({ productName: "Archived Product", withClass: ".selected" }),
            ]),
        ].flat(),
});

registry.category("web_tour.tours").add("test_order_invoice_search", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Desk Pad"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner Test 1"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickInvoiceButton(),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            Chrome.clickOrders(),
            TicketScreen.selectFilter("Paid"),
            TicketScreen.search("Invoice Number", "00001"),
            TicketScreen.nthRowContains(1, "001", false),
        ].flat(),
});

registry.category("web_tour.tours").add("test_order_with_existing_serial", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Serial Product"),
            ProductScreen.enterExistingLotNumber("SN1"),
            ProductScreen.selectedOrderlineHas("Serial Product", "1.00"),
            inLeftSide({
                trigger: ".info-list:contains('SN SN1')",
            }),
            ProductScreen.clickDisplayedProduct("Serial Product"),
            ProductScreen.enterExistingLotNumber("SN2"),
            ProductScreen.selectedOrderlineHas("Serial Product", "2.00"),
            inLeftSide({
                trigger: ".info-list:contains('SN SN2')",
            }),
        ].flat(),
});
