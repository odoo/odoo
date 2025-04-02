/** @odoo-module */

import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/utils/receipt_screen_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_ship_later_kit_and_mto_manufactured_product", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            ProductScreen.clickInfoProduct("Finished"),
            ProductScreen.priceOnProductInfoIs("10.00"),
            Dialog.confirm("Ok"),
            Dialog.isNot(),
            ProductScreen.clickInfoProduct("Basic Kit"),
            ProductScreen.priceOnProductInfoIs("10.00"),
            Dialog.confirm("Ok"),
            Dialog.isNot(),
            ProductScreen.addOrderline("Finished", "1"),
            ProductScreen.addOrderline("Basic Kit", "1"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner Full"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickShipLaterButton(),
            PaymentScreen.shippingLaterHighlighted(),
            PaymentScreen.clickValidate(),
            ReceiptScreen.receiptIsThere(),
        ].flat(),
});
