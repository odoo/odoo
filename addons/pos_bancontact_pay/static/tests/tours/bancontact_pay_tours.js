import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
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
            PaymentScreen.clickPaymentMethod("Bancontact - Display"), // bancontact_show_qr_code_0
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
            PaymentScreen.clickRetryButton(), // **bancontact_show_qr_code_1**
            PaymentScreen.qrPopupIsShown("2.00"),
            PaymentScreen.closeQrPopup(),
            PaymentScreen.showQrPopup({ selected: true }),
            PaymentScreen.qrPopupIsShown("2.00"),
            PaymentScreen.closeQrPopup(),

            // Sticker waiting
            PaymentScreen.clickPaymentMethod("Bancontact - Sticker 1"), // bancontact_show_qr_code_2
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
            PaymentScreen.clickRetryButton(), // **bancontact_show_qr_code_3**
            PaymentScreen.qrPopupIsNotShown(),
            PaymentScreen.showQrPopup({ selected: true }),
            PaymentScreen.qrPopupIsShown("3.00"),
            PaymentScreen.closeQrPopup(),

            // Open display sticker without selecting it and pay for the sticker
            PaymentScreen.showQrPopup({ name: "Bancontact - Display" }),
            PaymentScreen.qrPopupIsShown("2.00"),
            Bancontact.mockCallbackBancontactPay("bancontact_show_qr_code_3", "SUCCEEDED"),
            PaymentScreen.qrPopupIsShown("2.00"),

            // Pay now for the display
            Bancontact.mockCallbackBancontactPay("bancontact_show_qr_code_1", "SUCCEEDED"),
            PaymentScreen.qrPopupIsNotShown(),

            // Payment failed close qr
            PaymentScreen.clickPaymentMethod("Bancontact - Display"), // **bancontact_show_qr_code_4**
            PaymentScreen.selectedPaymentlineHas("Bancontact - Display", "5.00"),
            PaymentScreen.qrPopupIsShown("5.00"),
            Bancontact.mockCallbackBancontactPay("bancontact_show_qr_code_4", "FAILED"),
            PaymentScreen.qrPopupIsNotShown(),
        ].flat(),
});
