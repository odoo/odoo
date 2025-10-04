import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as Payconiq from "./utils/payconiq_utils.js";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";
import { registry } from "@web/core/registry";

const productScreenFlow = () =>
    [ProductScreen.addOrderline("Desk Pad", "1", "100"), ProductScreen.clickPayButton()].flat();

const initFlow = () =>
    [
        productScreenFlow(),
        PaymentScreen.clickPaymentMethod("Payconiq - Sticker 1"),
        Payconiq.isPaymentLinePending(),
        Payconiq.clickSendPayment(),
        Payconiq.isPaymentLineWaitingExternalQR(),
    ].flat();

const endFlow = () =>
    [
        Payconiq.isPaymentLineDone(),
        PaymentScreen.clickValidate(),
        ReceiptScreen.isShown(),
        ReceiptScreen.clickNextOrder(),
    ].flat();

const retryFlow = () =>
    [
        Payconiq.isPaymentLineRetry(),
        Payconiq.clickSendPayment(),
        Payconiq.isPaymentLineWaitingExternalQR(),
        Payconiq.mockCallbackPayconic("SUCCEEDED"),
    ].flat();

registry.category("web_tour.tours").add("payconiq_sticker_flow", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // Success webhook
            initFlow(),
            Payconiq.mockCallbackPayconic("IDENTIFIED"),
            Payconiq.isPaymentLineWaitingExternalQR(),
            Payconiq.mockCallbackPayconic("SUCCEEDED"),
            endFlow(),

            // Success webhook multiple stickers (002, 003)
            productScreenFlow(),
            PaymentScreen.clickPaymentMethod("Payconiq - Sticker 1"),
            Payconiq.isPaymentLinePending(),
            Payconiq.clickNewOrder(),
            productScreenFlow(),
            PaymentScreen.clickPaymentMethod("Payconiq - Sticker 2"),
            Payconiq.isPaymentLinePending(),
            Payconiq.clickSendPayment(),
            Payconiq.isPaymentLineWaitingExternalQR(),
            Payconiq.clickOrder("002"),
            Payconiq.isPaymentLinePending(),
            Payconiq.clickSendPayment(),
            Payconiq.isPaymentLineWaitingExternalQR(),
            Payconiq.mockCallbackPayconic("SUCCEEDED"),
            Payconiq.isPaymentLineDone(),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            Payconiq.clickOrder("003"),
            Payconiq.isPaymentLineWaitingExternalQR(),
            Payconiq.mockCallbackPayconic("SUCCEEDED", 2),
            Payconiq.isPaymentLineDone(),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            ReceiptScreen.clickNextOrder(),

            // Failed webhook and retry
            initFlow(),
            Payconiq.mockCallbackPayconic("FAILED"),
            retryFlow(),
            endFlow(),

            // Expired webhook and retry
            initFlow(),
            Payconiq.mockCallbackPayconic("EXPIRED"),
            retryFlow(),
            endFlow(),

            // Cancel webhook and retry
            initFlow(),
            Payconiq.mockCallbackPayconic("CANCELLED"),
            retryFlow(),
            endFlow(),

            // Click cancel and retry
            initFlow(),
            Payconiq.clickCancelPayment(),
            retryFlow(),
            endFlow(),

            // Confirm payment
            initFlow(),
            Payconiq.clickConfirmPayment(),
            endFlow(),
        ].flat(),
});
