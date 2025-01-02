import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as TicketScreen from "@point_of_sale/../tests/pos/tours/utils/ticket_screen_util";
import * as PosSale from "@pos_sale/../tests/tours/utils/pos_sale_utils";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as Order from "@point_of_sale/../tests/generic_helpers/order_widget_util";
import * as Utils from "@point_of_sale/../tests/generic_helpers/utils";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("PosSettleOrder", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            PosSale.settleNthOrder(1),
            ProductScreen.selectedOrderlineHas("Pizza Chicken", 9),
            ProductScreen.clickNumpad("Qty", "2"), // Change the quantity of the product to 2
            ProductScreen.selectedOrderlineHas("Pizza Chicken", 2),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            Chrome.clickOrders(),
        ].flat(),
});

registry.category("web_tour.tours").add("PosSettleOrderIncompatiblePartner", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            // The second item in the list is the first sale.order.
            PosSale.settleNthOrder(2),
            ProductScreen.selectedOrderlineHas("product1", 1),
            ProductScreen.totalAmountIs("10.00"),

            // The first item in the list is the second sale.order.
            // Selecting the 2nd sale.order should use a new order,
            // therefore, the total amount will change.
            PosSale.settleNthOrder(1),
            ProductScreen.selectedOrderlineHas("product2", 1),
            ProductScreen.totalAmountIs("11.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosSettleOrder2", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            PosSale.settleNthOrder(1),
            ProductScreen.clickOrderline("Product A", "1"),
            ProductScreen.selectedOrderlineHas("Product A", "1"),
            ProductScreen.clickOrderline("Product B", "1"),
            ProductScreen.clickNumpad("Qty", "0"),
            ProductScreen.selectedOrderlineHas("Product B", "0"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank", true, { remaining: "0.0" }),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("PosRefundDownpayment", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            PosSale.downPaymentFirstOrder("+10"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.clickNextOrder(),
            ...ProductScreen.clickRefund(),
            // Filter should be automatically 'Paid'.
            TicketScreen.filterIs("Paid"),
            TicketScreen.selectOrder("001"),
            Order.hasLine({
                productName: "Down Payment",
                withClass: ".selected",
                quantity: "1",
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
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            PosSale.settleNthOrder(1),
            ProductScreen.totalAmountIs(40),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("PosSettleOrder3", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            PosSale.settleNthOrder(1),
            ProductScreen.selectedOrderlineHas("Product A", "1"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank", true, { remaining: "0.0" }),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("PosSettleOrderNotGroupable", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            PosSale.settleNthOrder(1),
            ProductScreen.totalAmountIs(28.98), // 3.5 * 8 * 1.15 * 90%
            ProductScreen.selectedOrderlineHas("Product A", "0.5"),
            ProductScreen.checkOrderlinesNumber(4),
            ProductScreen.selectedOrderlineHas("Product A", "0.5", "4.14"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosSettleOrderWithNote", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            PosSale.settleNthOrder(1),
            Order.hasLine({
                customerNote: "Customer note 2--Customer note 3",
            }),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            // Check in the receipt
            Order.hasLine({
                customerNote: "Customer note 2--Customer note 3",
            }),
            ReceiptScreen.clickNextOrder(),
        ].flat(),
});

registry.category("web_tour.tours").add("PosSettleAndInvoiceOrder", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            PosSale.settleNthOrder(1),
            Order.hasLine({}),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickInvoiceButton(),
            PaymentScreen.clickValidate(),
        ].flat(),
});

registry.category("web_tour.tours").add("PosOrderDoesNotRemainInList", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            PosSale.settleNthOrder(1),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.clickNextOrder(),
            PosSale.checkOrdersListEmpty(),
        ].flat(),
});

registry.category("web_tour.tours").add("PosSettleDraftOrder", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            PosSale.settleNthOrder(1),
            ProductScreen.selectedOrderlineHas("Test service product", "1", "50.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosSettleCustomPrice", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            PosSale.settleNthOrder(1),
            ProductScreen.selectedOrderlineHas("Product A", "1", "100"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Test Partner AAA"),
            ProductScreen.selectedOrderlineHas("Product A", "1", "100"),
        ].flat(),
});

registry.category("web_tour.tours").add("PoSSaleOrderWithDownpayment", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            PosSale.settleNthOrder(1),
            ProductScreen.selectedOrderlineHas("Down Payment (POS)"),
            ProductScreen.totalAmountIs(980.0),
        ].flat(),
});

registry.category("web_tour.tours").add("PoSDownPaymentLinesPerTax", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            PosSale.downPaymentFirstOrder("+20"),
            Order.hasLine({
                productName: "Down Payment",
                quantity: "1",
                price: "2.20",
            }),
            Order.hasLine({
                productName: "Down Payment",
                quantity: "1",
                price: "1.00",
            }),
            Order.hasLine({
                productName: "Down Payment",
                quantity: "1",
                price: "3.00",
            }),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickInvoiceButton(),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("PoSApplyDownpayment", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            PosSale.downPaymentFirstOrder("+10"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
        ].flat(),
});

registry.category("web_tour.tours").add("PosShipLaterNoDefault", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            PosSale.settleNthOrder(1),
            ProductScreen.clickPayButton(),
            PaymentScreen.isShown(),
            Utils.negateStep(PaymentScreen.shippingLaterHighlighted()),
        ].flat(),
});

registry.category("web_tour.tours").add("PosSaleTeam", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Test Product"),
            ProductScreen.totalAmountIs("100.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
        ].flat(),
});

registry.category("web_tour.tours").add("PosOrdersListDifferentCurrency", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickControlButton("Quotation/Order"),
            {
                content: "Check that no orders are displayed",
                trigger: '.o_nocontent_help p:contains("No record found")',
            },
        ].flat(),
});

registry.category("web_tour.tours").add("PoSDownPaymentAmount", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            PosSale.downPaymentFirstOrder("+20"),
            Order.hasLine({
                productName: "Down Payment",
                quantity: "1",
                price: "20.0",
            }),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
        ].flat(),
});

registry.category("web_tour.tours").add("PosSettleOrder4", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            PosSale.settleNthOrder(1),
            ProductScreen.selectedOrderlineHas("Product A", "1"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.remainingIs("0.0"),
            PaymentScreen.clickShipLaterButton(),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("PosRepairSettleOrder", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            PosSale.settleNthOrder(1),
            ProductScreen.selectedOrderlineHas("Test Product", 1),
        ].flat(),
});

registry.category("web_tour.tours").add("PosSettleOrderShipLater", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            PosSale.settleNthOrder(1),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickShipLaterButton(),
            PaymentScreen.shippingLaterHighlighted(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.remainingIs("0.0"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("PosSettleOrder5", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            PosSale.settleNthOrder(1),
            ProductScreen.selectedOrderlineHas("Product A", "1.00"),
            Chrome.clickMenuOption("Backend"),
        ].flat(),
});
