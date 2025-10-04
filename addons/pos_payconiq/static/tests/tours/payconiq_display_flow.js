import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as Payconiq from "./utils/payconiq_utils.js";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";
import { registry } from "@web/core/registry";

const initFlow = () =>
    [
        ProductScreen.addOrderline("Desk Pad", "1", "100"),
        ProductScreen.clickPayButton(),
        PaymentScreen.clickPaymentMethod("Payconiq - Display"),
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

registry.category("web_tour.tours").add("payconiq_display_flow", {
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
