import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as TicketScreen from "@point_of_sale/../tests/pos/tours/utils/ticket_screen_util";
import * as Order from "@point_of_sale/../tests/generic_helpers/order_widget_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_pos_global_discount_sell_and_refund", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Desk Pad", "1", "3"),
            Chrome.clickOrders(),
            Order.hasLine({
                withoutClass: ".selected",
                run: "click",
                productName: "Desk Pad",
                quantity: "1",
            }),
            // Check that the draft order's order line is not selected and not causing issues while
            // comparing the line to the discount line
            {
                content: "Manually trigger keyup event",
                trigger: ".ticket-screen",
                run: function () {
                    window.dispatchEvent(new KeyboardEvent("keyup", { key: "9" }));
                },
            },
            TicketScreen.loadSelectedOrder(),
            ProductScreen.clickControlButton("Discount"),
            {
                content: `click discount numpad button: 5`,
                trigger: `.o_dialog div.numpad button:contains(5)`,
                run: "click",
            },
            Dialog.confirm(),
            ProductScreen.selectedOrderlineHas("discount", 1, "-0.15"),
            ProductScreen.totalAmountIs("2.85"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            ReceiptScreen.clickNextOrder(),
            ...ProductScreen.clickRefund(),
            TicketScreen.selectOrder("001"),
            ProductScreen.clickNumpad("1"),
            TicketScreen.toRefundTextContains("To Refund: 1"),
            ProductScreen.clickLine("discount"),
            ProductScreen.clickNumpad("1"),
            Dialog.confirm(),
            TicketScreen.confirmRefund(),
            PaymentScreen.isShown(),
            PaymentScreen.clickBack(),
            ProductScreen.clickLine("discount"),
            ProductScreen.clickNumpad("1"),
            Dialog.is({ title: "price update not allowed" }),
            Dialog.confirm(),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
        ].flat(),
});
