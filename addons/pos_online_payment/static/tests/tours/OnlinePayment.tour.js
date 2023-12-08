/** @odoo-module */

import * as ProductScreen from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import * as PaymentScreen from "@point_of_sale/../tests/tours/helpers/PaymentScreenTourMethods";
import * as Dialog from "@point_of_sale/../tests/tours/helpers/DialogTourMethods";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("OnlinePaymentErrorsTour", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            Dialog.confirm("Open session"),
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
            // successfully confirming the dialog would imply that the error popup is actually shown
            Dialog.confirm(),
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
            // successfully confirming the dialog would imply that the error popup is actually shown
            Dialog.confirm(),
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
            // successfully confirming the dialog would imply that the error popup is actually shown
            Dialog.confirm(),
        ].flat(),
});
