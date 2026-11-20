import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as TicketScreen from "@point_of_sale/../tests/pos/tours/utils/ticket_screen_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import { registry } from "@web/core/registry";
import {
    mockPaymobSaleCallback,
    mockPaymobRefundCallback,
} from "@pos_paymob/../tests/tours/utils/common";

registry.category("web_tour.tours").add("paymob_order_and_refund", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ProductScreen.addOrderline("Desk Pad"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Paymob"),
            {
                content: "Waiting for the Paymob terminal to process the payment",
                trigger: ".electronic_status:contains('Waiting for card')",
                run: async () => {
                    await mockPaymobSaleCallback();
                },
            },
            ReceiptScreen.isShown(),

            Chrome.clickOrders(),
            TicketScreen.selectFilter("Active"),
            TicketScreen.selectFilter("Paid"),
            TicketScreen.selectOrder("0001"),
            TicketScreen.confirmRefund(),
            PaymentScreen.clickPaymentMethod("Paymob"),
            PaymentScreen.clickRefundButton(),
            {
                content: "Waiting for the Paymob terminal to process the refund",
                // A refund line renders the waitingCard status as "Refund in process".
                trigger: ".electronic_status:contains('Refund in process')",
                run: async () => {
                    await mockPaymobRefundCallback();
                },
            },
            ReceiptScreen.isShown(),

            Chrome.endTour(),
        ].flat(),
});
