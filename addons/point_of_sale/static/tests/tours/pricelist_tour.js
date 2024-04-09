/** @odoo-module */

import { registry } from "@web/core/registry";
import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as Numpad from "@point_of_sale/../tests/tours/utils/numpad_util";
import * as Order from "@point_of_sale/../tests/tours/utils/generic_components/order_widget_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as Pricelist from "@point_of_sale/../tests/tours/utils/pricelist_util";

registry.category("web_tour.tours").add("pos_pricelist", {
    test: true,
    steps: () =>
        [
            Pricelist.setUp(),
            Pricelist.waitForUnitTest(),
            Dialog.confirm("Open session"),
            ProductScreen.clickPriceList("Fixed", true, "Public Pricelist"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Deco Addict"),
            ProductScreen.clickPriceList("Public Pricelist", true),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Lumber Inc"),
            ProductScreen.clickPriceList("Public Pricelist", true),
            ProductScreen.clickDisplayedProduct("Wall Shelf", true, "1.0"),
            ProductScreen.clickPriceList("min_quantity ordering"),
            ProductScreen.clickReview(),
            Numpad.click("2"),
            ProductScreen.goBackToMainScreen(),
            ProductScreen.selectedOrderlineHas("Wall Shelf", "2.0"),
            Order.hasTotal(`$ 2.00`),
            ProductScreen.clickDisplayedProduct("Small Shelf", true, "1.0"),
            ProductScreen.clickReview(),
            Numpad.click("Price"),
            Numpad.isActive("Price"),
            Numpad.click("5"),
            ...Order.hasLine({ productName: "Small Shelf", price: "5.0", withClass: ".selected" }),
            Numpad.click("Qty"),
            Numpad.isActive("Qty"),
            ProductScreen.goBackToMainScreen(),
            ProductScreen.clickPriceList("Public Pricelist"),
            Order.hasTotal(`$ 8.96`),
            ProductScreen.clickPriceList("min_quantity ordering"),
            ProductScreen.closePos(),
        ].flat(),
});
