/** @odoo-module */

import * as PaymentScreen from "@point_of_sale/../tests/tours/helpers/PaymentScreenTourMethods";
import * as ProductScreen from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/helpers/ReceiptScreenTourMethods";

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_ship_later_kit_and_mto_manufactured_product", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            ProductScreen.clickProductInfo("Finished"),
            ProductScreen.priceOnProductInfoIs("10.00"),
            ProductScreen.clickCloseProductInfo(),
            ProductScreen.clickProductInfo("Basic Kit"),
            ProductScreen.priceOnProductInfoIs("10.00"),
            ProductScreen.clickCloseProductInfo(),
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
