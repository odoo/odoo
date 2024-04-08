/** @odoo-module */

import * as ProductScreenPos from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as ProductScreenResto from "@pos_restaurant/../tests/tours/utils/product_screen_util";
const ProductScreen = { ...ProductScreenPos, ...ProductScreenResto };
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/utils/receipt_screen_util";
import * as FloorScreen from "@pos_restaurant/../tests/tours/utils/floor_screen_util";
import * as TicketScreen from "@point_of_sale/../tests/tours/utils/ticket_screen_util";
import * as Order from "@point_of_sale/../tests/tours/utils/generic_components/order_widget_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("RefundStayCurrentTableTour", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),

            // Create first order and pay it
            FloorScreen.clickTable("2"),
            ProductScreen.clickDisplayedProduct("Coca-Cola", true, "1.0"),
            ProductScreen.clickDisplayedProduct("Coca-Cola", true, "2.0"),
            ProductScreen.clickDisplayedProduct("Water", true, "1.0"),
            ProductScreen.totalAmountIs("6.60"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            {
                ...Dialog.confirm(),
                content:
                    "acknowledge printing error ( because we don't have printer in the test. )",
            },
            ReceiptScreen.clickNextOrder(),

            // Go to another table and refund one of the products
            FloorScreen.clickTable("4"),
            ProductScreen.orderIsEmpty(),
            ...ProductScreen.clickRefund(),
            TicketScreen.selectOrder("-0001"),
            Order.hasLine({
                productName: "Coca-Cola",
            }),
            ProductScreen.clickNumpad("2"),
            TicketScreen.toRefundTextContains("To Refund: 2.00"),
            TicketScreen.confirmRefund(),
            ProductScreen.isShown(),
            ProductScreen.selectedOrderlineHas("Coca-Cola"),
            ProductScreen.totalAmountIs("-4.40"),
        ].flat(),
});
