/** @odoo-module */

import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as PaymentScreenPos from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as PaymentScreenViva from "@pos_viva_wallet/../tests/tours/utils/payment_screen_viva_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
const PaymentScreen = { ...PaymentScreenPos, ...PaymentScreenViva };
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("VivaWalletTour", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            Dialog.confirm("Open session"),
            ProductScreen.addOrderline("Desk Pad", "1", "5.1", "5.1"),
            ProductScreen.clickPayButton(),
            PaymentScreen.isShown(),
            PaymentScreen.clickPaymentMethod("Viva"),
            PaymentScreen.isShown(),
        ].flat(),
});
