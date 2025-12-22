/** @odoo-module */

import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as Numpad from "@point_of_sale/../tests/tours/utils/numpad_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_03_pos_with_lots", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ProductScreen.clickDisplayedProduct("Monitor Stand"),
            ProductScreen.enterLotNumber("1"),
            ProductScreen.selectedOrderlineHas("Monitor Stand", "1"),
            ProductScreen.clickReview(),
            { ...ProductScreen.clickLine("Monitor Stand")[0], isActive: ["mobile"] },
            Numpad.click("2"),
            { ...ProductScreen.back(), isActive: ["mobile"] },
            ProductScreen.totalAmountIs("6.38"),
            ProductScreen.clickDisplayedProduct("Monitor Stand"),
            ProductScreen.enterLotNumber("2"),
            ProductScreen.clickReview(),
            { ...ProductScreen.clickLine("Monitor Stand")[0], isActive: ["mobile"] },
            Numpad.click("3"),
            { ...ProductScreen.back(), isActive: ["mobile"] },
            ProductScreen.totalAmountIs("15.95"),
            ProductScreen.clickPriceList("min_quantity ordering"),
            ProductScreen.totalAmountIs("5.00"),
            ProductScreen.clickReview(),
            { ...ProductScreen.clickLine("Monitor Stand")[0], isActive: ["mobile"] },
            Numpad.click("⌫"),
            { ...ProductScreen.back(), isActive: ["mobile"] },
            ProductScreen.totalAmountIs("6.38"),
            ProductScreen.isShown(),
        ].flat(),
});
