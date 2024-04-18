/** @odoo-module */

import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as ReceiptScreenPos from "@point_of_sale/../tests/tours/utils/receipt_screen_util";
import * as ReceiptScreenSale from "@pos_sale/../tests/tours/utils/receipt_screen_util";
import * as ProductScreenPos from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as ProductScreenSale from "@pos_sale/../tests/tours/utils/product_screen_util";
const ProductScreen = { ...ProductScreenPos, ...ProductScreenSale };
const ReceiptScreen = { ...ReceiptScreenPos, ...ReceiptScreenSale };
import * as TicketScreen from "@point_of_sale/../tests/tours/utils/ticket_screen_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as Order from "@point_of_sale/../tests/tours/utils/generic_components/order_widget_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("PosSettleOrder", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),
            ProductScreen.clickControlButton("Quotation/Order"),
            ProductScreen.selectFirstOrder(),
            ProductScreen.selectedOrderlineHas("Pizza Chicken", 9),
            ProductScreen.clickNumpad("Qty", "2"), // Change the quantity of the product to 2
            ProductScreen.selectedOrderlineHas("Pizza Chicken", 2),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            Chrome.clickMenuOption("Orders"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosSettleOrderIncompatiblePartner", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),
            ProductScreen.clickControlButton("Quotation/Order"),
            // The second item in the list is the first sale.order.
            ProductScreen.selectNthOrder(2),
            ProductScreen.selectedOrderlineHas("product1", 1),
            ProductScreen.totalAmountIs("10.00"),

            ProductScreen.clickControlButton("Quotation/Order"),
            // The first item in the list is the second sale.order.
            // Selecting the 2nd sale.order should use a new order,
            // therefore, the total amount will change.
            ProductScreen.selectNthOrder(1),
            ProductScreen.selectedOrderlineHas("product2", 1),
            ProductScreen.totalAmountIs("11.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosSettleOrder2", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),
            ProductScreen.clickControlButton("Quotation/Order"),
            ProductScreen.selectFirstOrder(),
            ProductScreen.clickOrderline("Product A", "1"),
            ProductScreen.selectedOrderlineHas("Product A", "1.00"),
            ProductScreen.clickOrderline("Product B", "1"),
            ProductScreen.clickNumpad("Qty", "0"),
            ProductScreen.selectedOrderlineHas("Product B", "0.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank", true, { remaining: "0.0" }),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("PosRefundDownpayment", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),
            ProductScreen.clickControlButton("Quotation/Order"),
            ProductScreen.downPaymentFirstOrder(),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.clickNextOrder(),
            ...ProductScreen.clickRefund(),
            // Filter should be automatically 'Paid'.
            TicketScreen.filterIs("Paid"),
            TicketScreen.selectOrder("-0001"),
            Order.hasLine({
                productName: "Down Payment",
                withClass: ".selected",
                quantity: "1.0",
            }),
            ProductScreen.clickNumpad("1"),
            TicketScreen.confirmRefund(),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.clickNextOrder(),
        ].flat(),
});

registry.category("web_tour.tours").add("PosSettleOrderRealTime", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),
            ProductScreen.clickControlButton("Quotation/Order"),
            ProductScreen.selectFirstOrder(),
            ProductScreen.totalAmountIs(40),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("PosSettleOrder3", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),
            ProductScreen.clickControlButton("Quotation/Order"),
            ProductScreen.selectFirstOrder(),
            ProductScreen.selectedOrderlineHas("Product A", "1.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank", true, { remaining: "0.0" }),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("PosSettleOrderNotGroupable", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),
            ProductScreen.clickControlButton("Quotation/Order"),
            ProductScreen.selectFirstOrder(),
            ProductScreen.totalAmountIs(32.2), // 3.5 * 8 * 1.15
            ProductScreen.selectedOrderlineHas("Product A", "0.50"),
            ProductScreen.checkOrderlinesNumber(4),
        ].flat(),
});

registry.category("web_tour.tours").add("PosSettleOrderWithNote", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),
            ProductScreen.clickControlButton("Quotation/Order"),
            ProductScreen.selectFirstOrder(),
            ProductScreen.checkCustomerNotes("Customer note 2--Customer note 3"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.checkCustomerNotes("Customer note 2--Customer note 3"),
            ReceiptScreen.clickNextOrder(),
        ].flat(),
});

registry.category("web_tour.tours").add("PosSettleAndInvoiceOrder", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),
            ProductScreen.clickControlButton("Quotation/Order"),
            ProductScreen.selectFirstOrder(),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickInvoiceButton(),
            PaymentScreen.clickValidate(),
        ].flat(),
});
