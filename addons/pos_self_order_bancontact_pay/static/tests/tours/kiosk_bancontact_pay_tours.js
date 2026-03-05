import { registry } from "@web/core/registry";
import * as Utils from "@pos_self_order/../tests/tours/utils/common";
import * as CartPage from "@pos_self_order/../tests/tours/utils/cart_page_util";
import * as ConfirmationPage from "@pos_self_order/../tests/tours/utils/confirmation_page_util";
import * as ProductPage from "@pos_self_order/../tests/tours/utils/product_page_util";
import * as PosBancontactPay from "@pos_bancontact_pay/../tests/tours/utils/bancontact_pay_utils";
import * as KioskBancontactPay from "@pos_self_order_bancontact_pay/../tests/tours/utils/kiosk_bancontact_pay_utils";
const BancontactPay = { ...PosBancontactPay, ...KioskBancontactPay };

registry.category("web_tour.tours").add("kiosk_bancontact_pay_success", {
    steps: () =>
        [
            Utils.clickBtn("Order Now"),
            ProductPage.clickProduct("Letter Tray"),
            Utils.clickBtn("Checkout"),
            CartPage.checkProduct("Letter Tray", "5.28"),
            Utils.clickBtn("Pay"), // **kiosk_bancontact_success_0**
            BancontactPay.processingPaymentStep(),
            BancontactPay.scanQrCodeStep(),
            BancontactPay.mockCallbackBancontactPay("kiosk_bancontact_success_0", "SUCCEEDED"),
            ConfirmationPage.isShown(),
            Utils.clickBtn("Close"),
            Utils.checkIsNoBtn("My Order"),
        ].flat(),
});

registry.category("web_tour.tours").add("kiosk_bancontact_pay_failed", {
    steps: () =>
        [
            Utils.clickBtn("Order Now"),
            ProductPage.clickProduct("Letter Tray"),
            Utils.clickBtn("Checkout"),
            CartPage.checkProduct("Letter Tray", "5.28"),
            Utils.clickBtn("Pay"), // **kiosk_bancontact_failed_0**
            BancontactPay.processingPaymentStep(),
            BancontactPay.scanQrCodeStep(),
            BancontactPay.mockCallbackBancontactPay("kiosk_bancontact_failed_0", "FAILED"),
            BancontactPay.scanQrCodeStep(),
            BancontactPay.notifiedDanger("Payment failed"),
            Utils.clickBtn("Retry"), // **kiosk_bancontact_failed_1**
            BancontactPay.processingPaymentStep(),
            BancontactPay.scanQrCodeStep(),
            BancontactPay.mockCallbackBancontactPay("kiosk_bancontact_failed_1", "SUCCEEDED"),
            ConfirmationPage.isShown(),
            Utils.clickBtn("Close"),
            Utils.checkIsNoBtn("My Order"),
        ].flat(),
});

const memo = {};
registry.category("web_tour.tours").add("kiosk_bancontact_pay_failed_create_payment", {
    steps: () =>
        [
            BancontactPay.setupBancontactErrorHttp(memo),
            Utils.clickBtn("Order Now"),
            ProductPage.clickProduct("Letter Tray"),
            Utils.clickBtn("Checkout"),
            CartPage.checkProduct("Letter Tray", "5.28"),
            Utils.clickBtn("Pay"),
            BancontactPay.processingPaymentStep(),
            BancontactPay.notifiedDanger("An error has occurred"),
            BancontactPay.bancontactDialogError(),
            Utils.clickBtn("Retry"),
            BancontactPay.teardownBancontactErrorHttp(memo),
            BancontactPay.processingPaymentStep(),
            BancontactPay.notifiedDanger("An error has occurred"),
        ].flat(),
});
