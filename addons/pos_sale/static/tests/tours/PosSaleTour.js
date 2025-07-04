/** @odoo-module */

import * as Chrome from "@point_of_sale/../tests/tours/helpers/ChromeTourMethods";
import * as PaymentScreen from "@point_of_sale/../tests/tours/helpers/PaymentScreenTourMethods";
import * as ReceiptScreenPos from "@point_of_sale/../tests/tours/helpers/ReceiptScreenTourMethods";
import * as ReceiptScreenSale from "@pos_sale/../tests/helpers/ReceiptScreenTourMethods";
import * as ProductScreenPos from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import * as ProductScreenSale from "@pos_sale/../tests/helpers/ProductScreenTourMethods";
const ProductScreen = { ...ProductScreenPos, ...ProductScreenSale };
const ReceiptScreen = { ...ReceiptScreenPos, ...ReceiptScreenSale };
import * as TicketScreen from "@point_of_sale/../tests/tours/helpers/TicketScreenTourMethods";
import * as Order from "@point_of_sale/../tests/tours/helpers/generic_components/OrderWidgetMethods";
import { negateStep } from "@point_of_sale/../tests/tours/helpers/utils";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("PosSettleOrder", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.clickQuotationButton(),
            ProductScreen.selectFirstOrder(),
            ProductScreen.selectedOrderlineHas("Pizza Chicken", 9),
            ProductScreen.pressNumpad("Qty", "2"), // Change the quantity of the product to 2
            ProductScreen.selectedOrderlineHas("Pizza Chicken", 2),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            Chrome.clickMenuButton(),
            Chrome.clickTicketButton(),
        ].flat(),
});

registry.category("web_tour.tours").add("PosSettleOrderIncompatiblePartner", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.clickQuotationButton(),
            // The second item in the list is the first sale.order.
            ProductScreen.selectNthOrder(2),
            ProductScreen.selectedOrderlineHas("product1", 1),
            ProductScreen.totalAmountIs("10.00"),

            ProductScreen.clickQuotationButton(),
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
    url: "/pos/ui",
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.clickQuotationButton(),
            ProductScreen.selectFirstOrder(),
            ProductScreen.clickOrderline("Product A", "1"),
            ProductScreen.selectedOrderlineHas("Product A", "1.00"),
            ProductScreen.clickOrderline("Product B", "1"),
            ProductScreen.pressNumpad("Qty", "0"),
            ProductScreen.selectedOrderlineHas("Product B", "0.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.remainingIs("0.0"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("PosRefundDownpayment", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            ProductScreen.clickQuotationButton(),
            ProductScreen.downPaymentFirstOrder(),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.clickNextOrder(),
            ProductScreen.clickRefund(),
            // Filter should be automatically 'Paid'.
            TicketScreen.filterIs("Paid"),
            TicketScreen.selectOrder("-0001"),
            Order.hasLine({
                productName: "Down Payment",
                withClass: ".selected",
                quantity: "1.0",
            }),
            ProductScreen.pressNumpad("1"),
            TicketScreen.confirmRefund(),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.clickNextOrder(),
        ].flat(),
});

registry.category("web_tour.tours").add("PosSettleOrderRealTime", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.clickQuotationButton(),
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
    url: "/pos/ui",
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.clickQuotationButton(),
            ProductScreen.selectFirstOrder(),
            ProductScreen.selectedOrderlineHas("Product A", "1.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.remainingIs("0.0"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("PosSettleOrderNotGroupable", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.clickQuotationButton(),
            ProductScreen.selectFirstOrder(),
            ProductScreen.totalAmountIs(28.98), // 3.5 * 8 * 1.15 * 90%
            ProductScreen.selectedOrderlineHas("Product A", "0.50"),
            ProductScreen.checkOrderlinesNumber(4),
            ProductScreen.selectedOrderlineHas('Product A', '0.5', '4.14'),
        ].flat(),
});

registry.category("web_tour.tours").add("PosSettleOrderWithNote", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.clickQuotationButton(),
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
    url: "/pos/ui",
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.clickQuotationButton(),
            ProductScreen.selectFirstOrder(),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickInvoiceButton(),
            PaymentScreen.clickValidate(),
        ].flat(),
});

registry.category("web_tour.tours").add("PosQuotationSaving", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.clickQuotationButton(),
            ProductScreen.selectFirstOrder(),
            ProductScreen.selectedOrderlineHas("Product", "4.00", "40.00"),
            ProductScreen.clickSave(),
        ].flat(),
});

registry.category("web_tour.tours").add("PosOrderDoesNotRemainInList", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.clickQuotationButton(),
            ProductScreen.selectFirstOrder(),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.clickNextOrder(),
            ProductScreen.clickQuotationButton(),
            ProductScreen.checkOrdersListEmpty(),
        ].flat(),
});

registry.category("web_tour.tours").add("PosSettleCustomPrice", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.clickQuotationButton(),
            ProductScreen.selectFirstOrder(),
            ProductScreen.selectedOrderlineHas('product_a', '1', '100'),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Test Partner AAA"),
            ProductScreen.selectedOrderlineHas('product_a', '1', '100'),
        ].flat(),
});

registry.category("web_tour.tours").add("PosSettleDraftOrder", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.clickQuotationButton(),
            ProductScreen.selectFirstOrder(),
            ProductScreen.selectedOrderlineHas('Test service product', '1.00', '50.00'),
        ].flat(),
});

registry.category("web_tour.tours").add("PoSDownPaymentLinesPerTax", {
    test: true,
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.clickQuotationButton(),
            ProductScreen.downPayment20PercentFirstOrder(),
            Order.hasLine({
                productName: "Down Payment",
                quantity: "1.0",
                price: "2.20",
            }),
            Order.hasLine({
                productName: "Down Payment",
                quantity: "1.0",
                price: "1.00",
            }),
            Order.hasLine({
                productName: "Down Payment",
                quantity: "1.0",
                price: "3.00",
            }),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickInvoiceButton(),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("PosShipLaterNoDefault", {
    test: true,
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.clickQuotationButton(),
            ProductScreen.selectFirstOrder(),
            ProductScreen.clickPayButton(),
            PaymentScreen.isShown(),
            negateStep(PaymentScreen.shippingLaterHighlighted()),
        ].flat(),
});

registry.category("web_tour.tours").add("PoSDownPaymentAmount", {
    test: true,
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.clickQuotationButton(),
            ProductScreen.downPayment20PercentFirstOrder(),
            Order.hasLine({
                productName: "Down Payment",
                quantity: "1.0",
                price: "20.0",
            }),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
        ].flat(),
});

registry.category("web_tour.tours").add("PosSettleOrder4", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.clickQuotationButton(),
            ProductScreen.selectFirstOrder(),
            ProductScreen.selectedOrderlineHas("Product A", "1.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.remainingIs("0.0"),
            PaymentScreen.clickShipLaterButton(),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("PosSettleOrderShipLater", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.clickQuotationButton(),
            ProductScreen.selectNthOrder(2),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickShipLaterButton(),
            PaymentScreen.shippingLaterHighlighted(),
            PaymentScreen.clickPaymentMethod('Bank'),
            PaymentScreen.remainingIs('0.0'),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            ReceiptScreen.clickNextOrder(),
            ProductScreen.clickQuotationButton(),
            ProductScreen.selectNthOrder(1),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickShipLaterButton(),
            PaymentScreen.shippingLaterHighlighted(),
            PaymentScreen.clickPaymentMethod('Bank'),
            PaymentScreen.remainingIs('0.0'),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("PoSDownPaymentFixedTax", {
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.clickQuotationButton(),
            ProductScreen.downPayment20PercentFirstOrder(),
            Order.hasLine({
                productName: "Down Payment",
                quantity: "1.0",
                price: "1.00",
            }),
            Order.hasLine({
                productName: "Down Payment",
                quantity: "1.0",
                price: "22.00",
            }),
        ].flat(),
});

registry.category("web_tour.tours").add("test_multiple_lots_sale_order", {
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.clickQuotationButton(),
            ProductScreen.selectNthOrder(1, { loadSN: true }),
            {
                'content': 'Ensure first line has lot 1001',
                'trigger': '.order-container .orderline:nth-child(1):contains(Product):contains(1001)',
            },
            {
                'content': 'Ensure second line has lot 1002',
                'trigger': '.order-container .orderline:nth-child(2):contains(Product):contains(1002)',
            },
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
        ].flat(),
});
