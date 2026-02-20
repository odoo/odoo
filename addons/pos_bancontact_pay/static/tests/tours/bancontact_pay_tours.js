import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as FeedbackScreen from "@point_of_sale/../tests/pos/tours/utils/feedback_screen_util";
import * as Numpad from "@point_of_sale/../tests/generic_helpers/numpad_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as Order from "@point_of_sale/../tests/generic_helpers/order_widget_util";
import * as Bancontact from "./utils/bancontact_pay_utils.js";
import { registry } from "@web/core/registry";

const initOrder = () =>
    [
        ProductScreen.clickDisplayedProduct("Desk Pad"),
        Numpad.click("Price"),
        Numpad.enterValue("10"),
        Order.hasLine({ productName: "Desk Pad", price: "10.00" }),
        ProductScreen.clickPayButton(),
    ].flat();

const memo = {};
registry.category("web_tour.tours").add("bancontact_pay_failed_to_create_payment", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            initOrder(),

            // Add a new payment line using Bancontact but the request return an error 401
            Bancontact.setupBancontactErrorHttp(memo),
            PaymentScreen.clickPaymentMethod("Bancontact - Display"),
            Bancontact.apiErrorDialog(401),
            PaymentScreen.hasActionState("retry"),

            // Retry to send the payment via the action state button
            PaymentScreen.clickRetryButton(),
            Bancontact.apiErrorDialog(401),
            Bancontact.teardownBancontactErrorHttp(memo),

            // Delete the faulty payment line
            PaymentScreen.clickPaymentlineDelButton("Bancontact - Display", "10.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("bancontact_pay_can_send_request", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            initOrder(),

            // Order 1001 - Display [A]
            PaymentScreen.clickPaymentMethod("Bancontact - Display"),
            PaymentScreen.closeQrPopup(),
            PaymentScreen.hasActionState("waiting_scan"),

            // Order 1001 - Display [B]
            PaymentScreen.clickPaymentMethod("Bancontact - Display"),
            PaymentScreen.closeQrPopup(),
            PaymentScreen.hasActionState("waiting_scan"),

            // Order 1001 - Sticker 1 [C]
            PaymentScreen.clickPaymentMethod("Bancontact - Sticker 1"),
            PaymentScreen.hasActionState("waiting_scan"),

            // ERROR + Not created => Order 1001 - Sticker 1 [D]
            PaymentScreen.clickPaymentMethod("Bancontact - Sticker 1"),
            Bancontact.stickerAlreadyProcessingDialog(),
            PaymentScreen.countPaymentlinesIs(3),

            // Cancel C and retry creating D
            PaymentScreen.clickPaymentline("Bancontact - Sticker 1", undefined, 3),
            PaymentScreen.clickCancelButton(),
            PaymentScreen.hasActionState("retry"),
            PaymentScreen.clickPaymentMethod("Bancontact - Sticker 1"),
            PaymentScreen.hasActionState("waiting_scan"),

            // ERROR => Retry C
            PaymentScreen.clickPaymentline("Bancontact - Sticker 1", undefined, 3),
            PaymentScreen.clickRetryButton(),
            Bancontact.stickerAlreadyProcessingDialog(),
            PaymentScreen.hasActionState("retry"),

            // Order 1001 - Sticker 2 [E]
            PaymentScreen.clickPaymentMethod("Bancontact - Sticker 2"),
            PaymentScreen.hasActionState("waiting_scan"),

            // Order 1002 - Display [F]
            Chrome.createFloatingOrder(),
            initOrder(),
            PaymentScreen.clickPaymentMethod("Bancontact - Display"),
            PaymentScreen.closeQrPopup(),
            PaymentScreen.hasActionState("waiting_scan"),

            // ERROR + Not created =>  Order 1002 - Sticker 2 [G]
            PaymentScreen.clickPaymentMethod("Bancontact - Sticker 2"),
            Bancontact.stickerAlreadyProcessingDialog(),
            PaymentScreen.countPaymentlinesIs(1),

            // Cancel E and retry creating G
            Chrome.clickFloatingOrder("1001"),
            PaymentScreen.clickPaymentline("Bancontact - Sticker 2", undefined, 5),
            PaymentScreen.clickCancelButton(),
            PaymentScreen.hasActionState("retry"),
            Chrome.clickFloatingOrder("1002"),
            PaymentScreen.clickPaymentMethod("Bancontact - Sticker 2"),
            PaymentScreen.hasActionState("waiting_scan"),

            // ERROR => Retry E
            Chrome.clickFloatingOrder("1001"),
            PaymentScreen.clickPaymentline("Bancontact - Sticker 2", undefined, 5),
            PaymentScreen.clickRetryButton(),
            Bancontact.stickerAlreadyProcessingDialog(),
            PaymentScreen.hasActionState("retry"),
        ].flat(),
});

registry.category("web_tour.tours").add("bancontact_pay_show_qr_code", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            initOrder(),

            // Display waiting
            PaymentScreen.clickPaymentMethod("Bancontact - Display"),
            PaymentScreen.selectedPaymentlineHas("Bancontact - Display", "10.00"),
            PaymentScreen.qrPopupIsShown("10.00"),
            PaymentScreen.closeQrPopup(),
            PaymentScreen.showQrPopup({ selected: true }),
            PaymentScreen.qrPopupIsShown("10.00"),
            PaymentScreen.closeQrPopup(),

            // Display cancel
            PaymentScreen.clickCancelButton(),
            PaymentScreen.showQrPopupIsDisabled(),

            // Display retry
            PaymentScreen.enterPaymentLineAmount("Bancontact - Display", "2"),
            PaymentScreen.selectedPaymentlineHas("Bancontact - Display", "2.00"),
            PaymentScreen.clickRetryButton(),
            PaymentScreen.qrPopupIsShown("2.00"),
            PaymentScreen.closeQrPopup(),
            PaymentScreen.showQrPopup({ selected: true }),
            PaymentScreen.qrPopupIsShown("2.00"),
            PaymentScreen.closeQrPopup(),

            // Sticker waiting
            PaymentScreen.clickPaymentMethod("Bancontact - Sticker 1"),
            PaymentScreen.selectedPaymentlineHas("Bancontact - Sticker 1", "10.00"),
            PaymentScreen.qrPopupIsNotShown(),
            PaymentScreen.showQrPopup({ selected: true }),
            PaymentScreen.qrPopupIsShown("10.00"),
            PaymentScreen.closeQrPopup(),

            // Sticker cancel
            PaymentScreen.clickCancelButton(),
            PaymentScreen.showQrPopupIsDisabled(),

            // Sticker retry
            PaymentScreen.enterPaymentLineAmount("Bancontact - Sticker 1", "3"),
            PaymentScreen.selectedPaymentlineHas("Bancontact - Sticker 1", "3.00"),
            PaymentScreen.clickRetryButton(),
            PaymentScreen.qrPopupIsNotShown(),
            PaymentScreen.showQrPopup({ selected: true }),
            PaymentScreen.qrPopupIsShown("3.00"),
            PaymentScreen.closeQrPopup(),

            // Open display sticker without selecting it and pay for the sticker
            PaymentScreen.showQrPopup({ name: "Bancontact - Display" }),
            PaymentScreen.qrPopupIsShown("2.00"),
            Bancontact.mockCallbackBancontactPay("SUCCEEDED"),
            PaymentScreen.qrPopupIsShown("2.00"),

            // Pay now for the display
            Bancontact.mockCallbackBancontactPay("SUCCEEDED", 2),
            PaymentScreen.qrPopupIsNotShown(),

            // Payment failed close qr
            PaymentScreen.clickPaymentMethod("Bancontact - Display"),
            PaymentScreen.selectedPaymentlineHas("Bancontact - Display", "5.00"),
            PaymentScreen.qrPopupIsShown("5.00"),
            Bancontact.mockCallbackBancontactPay("FAILED"),
            PaymentScreen.qrPopupIsNotShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("bancontact_pay_success_payment", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            initOrder(),

            // Order 1001 - Display 5€ [A]
            PaymentScreen.clickPaymentMethod("Bancontact - Display"),
            PaymentScreen.selectedPaymentlineHas("Bancontact - Display", "10.00"),
            PaymentScreen.closeQrPopup(),
            PaymentScreen.clickCancelButton(),
            PaymentScreen.hasActionState("retry"),
            PaymentScreen.enterPaymentLineAmount("Bancontact - Display", "5"),
            PaymentScreen.selectedPaymentlineHas("Bancontact - Display", "5.00"),
            PaymentScreen.clickRetryButton(),
            PaymentScreen.closeQrPopup(),
            PaymentScreen.hasActionState("waiting_scan"),

            // Order 1001 - Display 2€ [B]
            PaymentScreen.clickPaymentMethod("Bancontact - Display"),
            PaymentScreen.selectedPaymentlineHas("Bancontact - Display", "10.00"),
            PaymentScreen.closeQrPopup(),
            PaymentScreen.clickCancelButton(),
            PaymentScreen.hasActionState("retry"),
            PaymentScreen.enterPaymentLineAmount("Bancontact - Display", "2"),
            PaymentScreen.selectedPaymentlineHas("Bancontact - Display", "2.00"),
            PaymentScreen.clickRetryButton(),
            PaymentScreen.closeQrPopup(),
            PaymentScreen.hasActionState("waiting_scan"),

            // Pay payment line A while being on another payment line - notified
            Bancontact.mockCallbackBancontactPay("SUCCEEDED", 2),
            Bancontact.notifiedPaymentReceived(),
            PaymentScreen.clickPaymentline("Bancontact - Display", "5"),
            PaymentScreen.hasActionState("paid"),
            PaymentScreen.clickPaymentline("Bancontact - Display", "2"),
            PaymentScreen.hasActionState("waiting_scan"),

            // Pay payment line B
            Bancontact.mockCallbackBancontactPay("SUCCEEDED", 1),
            PaymentScreen.hasActionState("paid"),

            // Order 1001 - Display 3€ (fully paid) [C]
            PaymentScreen.clickPaymentMethod("Bancontact - Display"),
            PaymentScreen.selectedPaymentlineHas("Bancontact - Display", "3.00"),
            PaymentScreen.hasActionState("waiting_scan"),

            // Pay payment line C - Autovalidate order
            Bancontact.mockCallbackBancontactPay("SUCCEEDED"),
            FeedbackScreen.isShown(),
            FeedbackScreen.clickNextOrder(),

            // Order 1002 - Display 5€ [D]
            initOrder(),
            PaymentScreen.clickPaymentMethod("Bancontact - Display"),
            PaymentScreen.selectedPaymentlineHas("Bancontact - Display", "10.00"),
            PaymentScreen.closeQrPopup(),
            PaymentScreen.clickCancelButton(),
            PaymentScreen.hasActionState("retry"),
            PaymentScreen.enterPaymentLineAmount("Bancontact - Display", "5"),
            PaymentScreen.selectedPaymentlineHas("Bancontact - Display", "5.00"),
            PaymentScreen.clickRetryButton(),
            PaymentScreen.closeQrPopup(),
            PaymentScreen.hasActionState("waiting_scan"),

            // Pay payment line D while on another order - notified
            Chrome.createFloatingOrder(),
            Bancontact.mockCallbackBancontactPay("SUCCEEDED"),
            Bancontact.notifiedOrderPartiallyPaid("1002"),

            // Order 1002 - Display 5€ (fully paid) [E]
            Chrome.clickFloatingOrder("1002"),
            PaymentScreen.clickPaymentMethod("Bancontact - Display"),
            PaymentScreen.selectedPaymentlineHas("Bancontact - Display", "5.00"),
            PaymentScreen.closeQrPopup(),
            PaymentScreen.hasActionState("waiting_scan"),

            // Pay payment line E while on another order - notified + NOT autovalidate
            Chrome.clickFloatingOrder("1003"),
            Bancontact.mockCallbackBancontactPay("SUCCEEDED"),
            Bancontact.notifiedOrderFullyPaid("1002"),
            Chrome.clickFloatingOrder("1002"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),

            // Order 1003 - Force done payment [F] - autovalidate
            FeedbackScreen.clickNextOrder(),
            initOrder(),
            PaymentScreen.clickPaymentMethod("Bancontact - Display"),
            PaymentScreen.selectedPaymentlineHas("Bancontact - Display", "10.00"),
            PaymentScreen.closeQrPopup(),
            PaymentScreen.hasActionState("waiting_scan"),
            PaymentScreen.clickForceDoneButton(),
            FeedbackScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("bancontact_pay_failed_payment", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            initOrder(),

            // Simulate a AUTHORIZATION_FAILED payment from Bancontact side
            PaymentScreen.clickPaymentMethod("Bancontact - Display"),
            PaymentScreen.hasActionState("waiting_scan"),
            Bancontact.mockCallbackBancontactPay("AUTHORIZATION_FAILED"),
            PaymentScreen.hasActionState("retry"),
            Bancontact.notifiedPaymentError("Payment failed"),

            // Simulate a FAILED payment from Bancontact side
            PaymentScreen.clickPaymentMethod("Bancontact - Display"),
            PaymentScreen.hasActionState("waiting_scan"),
            Bancontact.mockCallbackBancontactPay("FAILED"),
            PaymentScreen.hasActionState("retry"),
            Bancontact.notifiedPaymentError("Payment failed"),

            // Simulate a EXPIRED payment from Bancontact side
            PaymentScreen.clickPaymentMethod("Bancontact - Display"),
            PaymentScreen.hasActionState("waiting_scan"),
            Bancontact.mockCallbackBancontactPay("EXPIRED"),
            PaymentScreen.hasActionState("retry"),
            Bancontact.notifiedPaymentError("Payment expired"),

            // Simulate a CANCELLED payment from Bancontact side
            PaymentScreen.clickPaymentMethod("Bancontact - Display"),
            PaymentScreen.hasActionState("waiting_scan"),
            Bancontact.mockCallbackBancontactPay("CANCELLED"),
            PaymentScreen.hasActionState("retry"),
            Bancontact.notifiedPaymentError("Payment cancelled"),

            // Failed while not current order
            PaymentScreen.clickPaymentMethod("Bancontact - Display"),
            PaymentScreen.closeQrPopup(),
            Chrome.createFloatingOrder(),
            Bancontact.mockCallbackBancontactPay("FAILED"),
            Bancontact.notifiedPaymentError("A payment for order 1001 has failed."),
        ].flat(),
});

registry.category("web_tour.tours").add("bancontact_pay_failed_to_cancel_payment_error_422", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            initOrder(),

            // Add a new payment line using Bancontact
            PaymentScreen.clickPaymentMethod("Bancontact - Display"),
            PaymentScreen.closeQrPopup(),
            PaymentScreen.hasActionState("waiting_scan"),

            // Cancel the payment with an error 422 thrown --> ask to force cancel the payment
            PaymentScreen.clickCancelButton(),
            Bancontact.askForceCancelDialog("close"),
            PaymentScreen.hasActionState("waiting_scan"),

            // Force cancel the payment
            PaymentScreen.clickCancelButton(),
            Bancontact.askForceCancelDialog("force_cancel"),
            PaymentScreen.hasActionState("retry"),

            // Can retry to send the payment
            PaymentScreen.clickRetryButton(),
            PaymentScreen.closeQrPopup(),
            PaymentScreen.hasActionState("waiting_scan"),
        ].flat(),
});

registry.category("web_tour.tours").add("bancontact_pay_failed_to_cancel_payment_error_429", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            initOrder(),

            // Add a new payment line using Bancontact
            PaymentScreen.clickPaymentMethod("Bancontact - Display"),
            PaymentScreen.closeQrPopup(),
            PaymentScreen.hasActionState("waiting_scan"),

            // Cancel the payment with an error 429 thrown --> caught and ignore the error
            PaymentScreen.clickCancelButton(),
            PaymentScreen.hasActionState("retry"),

            // Can retry to send the payment
            PaymentScreen.clickRetryButton(),
            PaymentScreen.closeQrPopup(),
            PaymentScreen.hasActionState("waiting_scan"),
        ].flat(),
});
