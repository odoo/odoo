/** @odoo-module */

import * as ProductScreen from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import * as PaymentScreen from "@point_of_sale/../tests/tours/helpers/PaymentScreenTourMethods";
import * as OnlinePaymentPopup from "@pos_online_payment/../tests/tours/helpers/OnlinePaymentPopupTourMethods";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/helpers/ReceiptScreenTourMethods";
import * as ErrorPopup from "@point_of_sale/../tests/tours/helpers/ErrorPopupTourMethods";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("OnlinePaymentLocalFakePaidDataTour", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.addOrderline("Letter Tray", "10"),
            ProductScreen.selectedOrderlineHas("Letter Tray", "10.0"),
            ProductScreen.clickPayButton(),
            PaymentScreen.totalIs("48.0"),
            PaymentScreen.emptyPaymentlines("48.0"),

            PaymentScreen.clickPaymentMethod("Online payment"),
            PaymentScreen.enterPaymentLineAmount("Online payment", "48"),
            PaymentScreen.selectedPaymentlineHas("Online payment", "48.0"),
            PaymentScreen.remainingIs("0.0"),
            PaymentScreen.changeIs("0.0"),
            PaymentScreen.validateButtonIsHighlighted(true),
            PaymentScreen.clickValidate(),
            OnlinePaymentPopup.isShown(),
            OnlinePaymentPopup.amountIs("48.0"),
            OnlinePaymentPopup.fakeOnlinePaymentPaidData(),
            OnlinePaymentPopup.isNotShown(),
            ReceiptScreen.isShown(),
            ReceiptScreen.receiptIsThere(),
        ].flat(),
});

registry.category("web_tour.tours").add("OnlinePaymentErrorsTour", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.addOrderline("Letter Tray", "10"),
            ProductScreen.selectedOrderlineHas("Letter Tray", "10.0"),
            ProductScreen.clickPayButton(),
            PaymentScreen.totalIs("48.0"),
            PaymentScreen.emptyPaymentlines("48.0"),

            PaymentScreen.clickPaymentMethod("Online payment"),
            PaymentScreen.enterPaymentLineAmount("Online payment", "47"),
            PaymentScreen.selectedPaymentlineHas("Online payment", "47.0"),
            PaymentScreen.remainingIs("1.0"),
            PaymentScreen.changeIs("0.0"),
            PaymentScreen.validateButtonIsHighlighted(false),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.enterPaymentLineAmount("Cash", "2"),
            PaymentScreen.selectedPaymentlineHas("Cash", "2.0"),
            PaymentScreen.remainingIs("0.0"),
            PaymentScreen.changeIs("1.0"),
            PaymentScreen.validateButtonIsHighlighted(true),
            PaymentScreen.clickValidate(),
            ErrorPopup.isShown(),
            ErrorPopup.clickConfirm(),
            PaymentScreen.clickPaymentline("Online payment", "47.0"),
            PaymentScreen.clickPaymentlineDelButton("Online payment", "47.0"),
            PaymentScreen.clickPaymentMethod("Online payment"),
            PaymentScreen.selectedPaymentlineHas("Online payment", "46.0"),
            PaymentScreen.clickPaymentMethod("Online payment"),
            PaymentScreen.selectedPaymentlineHas("Online payment", "0.0"),
            PaymentScreen.remainingIs("0.0"),
            PaymentScreen.changeIs("0.0"),
            PaymentScreen.validateButtonIsHighlighted(true),
            PaymentScreen.clickValidate(),
            ErrorPopup.isShown(),
            ErrorPopup.clickConfirm(),
            PaymentScreen.clickPaymentline("Online payment", "0.0"),
            PaymentScreen.clickPaymentlineDelButton("Online payment", "0.0"),
            PaymentScreen.clickPaymentline("Cash", "2.0"),
            PaymentScreen.enterPaymentLineAmount("Cash", "3"),
            PaymentScreen.selectedPaymentlineHas("Cash", "3.0"),
            PaymentScreen.clickPaymentMethod("Online payment"),
            PaymentScreen.selectedPaymentlineHas("Online payment", "-1.0"),
            PaymentScreen.remainingIs("0.0"),
            PaymentScreen.changeIs("0.0"),
            PaymentScreen.validateButtonIsHighlighted(true),
            PaymentScreen.clickValidate(),
            ErrorPopup.isShown(),
            ErrorPopup.clickConfirm(),
        ].flat(),
});
