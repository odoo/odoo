/** @odoo-module */

import * as ProductScreen from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import * as PaymentScreenPos from "@point_of_sale/../tests/tours/helpers/PaymentScreenTourMethods";
import * as PaymentScreenViva from "@pos_viva_wallet/../tests/tours/helpers/PaymentScreenVivaTourMethods";
const PaymentScreen = { ...PaymentScreenPos, ...PaymentScreenViva };
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("VivaWalletTour", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.addOrderline("Desk Pad", "1", "5.1", "5.1"),
            ProductScreen.clickPayButton(),
            PaymentScreen.isShown(),
            PaymentScreen.clickPaymentMethod("Viva"),
            PaymentScreen.send_payment_request(),
            PaymentScreen.isShown(),
        ].flat(),
});
