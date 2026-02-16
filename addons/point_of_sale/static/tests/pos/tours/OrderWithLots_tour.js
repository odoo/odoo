/** @odoo-module */

import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as Numpad from "@point_of_sale/../tests/generic_helpers/numpad_util";
import * as PreparationReceipt from "@point_of_sale/../tests/pos/tours/utils/preparation_receipt_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_03_pos_with_lots", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ProductScreen.clickDisplayedProduct("Monitor Stand"),
            ProductScreen.enterLotNumber("1", "lot"),
            ProductScreen.selectedOrderlineHas("Monitor Stand", "1"),
            ProductScreen.clickReview(),
            { ...ProductScreen.clickLine("Monitor Stand")[0], isActive: ["mobile"] },
            Numpad.click("2"),
            { ...ProductScreen.back(), isActive: ["mobile"] },
            ProductScreen.totalAmountIs("6.38"),
            ProductScreen.clickDisplayedProduct("Monitor Stand"),
            ProductScreen.enterLotNumber("2", "lot"),
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
            ProductScreen.clickDisplayedProduct("Monitor Stand"),
            ProductScreen.enterLotNumber("147259", "lot"),
            {
                content: "Check the content of the preparation receipt for '147259' lot number",
                trigger: "body",
                run: async () => {
                    const receipts = await PreparationReceipt.generatePreparationReceipts();
                    if (!receipts[0].innerHTML.includes("147259")) {
                        throw new Error("Lot number 147259 not found in printed receipt");
                    }
                },
            },
        ].flat(),
});

registry.category("web_tour.tours").add("test_lot_tracking_without_lot_creation", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Monitor Stand"),
            ProductScreen.totalAmountIs("3.19"),
            ProductScreen.clickDisplayedProduct("Monitor Stand"),
            ProductScreen.totalAmountIs("6.38"),
        ].flat(),
});
