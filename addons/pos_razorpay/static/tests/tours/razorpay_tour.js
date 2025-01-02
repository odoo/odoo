import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as TicketScreen from "@point_of_sale/../tests/pos/tours/utils/ticket_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("PosRazorpayTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Desk Pad"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Razorpay"),
            ReceiptScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("PosRazorpayCancelTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Desk Pad"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("RazorPay"),
            PaymentScreen.clickCancelButton(),
            Dialog.is({ title: "Razorpay Error" }),
            Dialog.bodyIs("Razorpay POS transaction canceled successfully"),
            Dialog.confirm(),
            PaymentScreen.isShown(),
            PaymentScreen.clickRetryButton(),
            ReceiptScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("PosRazorpayRefundTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Desk Pad"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Razorpay"),
            ReceiptScreen.isShown(),
            ReceiptScreen.clickNextOrder(),
            ProductScreen.clickRefund(),
            TicketScreen.selectOrder("001"),
            TicketScreen.confirmRefund(),
            PaymentScreen.clickPaymentMethod("Razorpay"),
            PaymentScreen.clickRefundButton(),
            ReceiptScreen.isShown(),
        ].flat(),
});
