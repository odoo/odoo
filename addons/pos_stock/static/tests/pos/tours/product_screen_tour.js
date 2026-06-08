import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as StockProductScreen from "@pos_stock/../tests/pos/tours/utils/product_screen_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import { registry } from "@web/core/registry";
import { inLeftSide } from "@point_of_sale/../tests/pos/tours/utils/common";
import { scan_barcode, refresh } from "@point_of_sale/../tests/generic_helpers/utils";
import * as Numpad from "@point_of_sale/../tests/generic_helpers/numpad_util";

registry.category("web_tour.tours").add("limitedProductPricelistLoadingStock", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            scan_barcode("0100100"),
            ProductScreen.selectedOrderlineHas("Test Product 1", "1", "80.0"),

            scan_barcode("0100201"),
            StockProductScreen.enterLotNumber("1", "lot"),
            ProductScreen.selectedOrderlineHas("Test Product 2", "1", "100.0", "White"),

            scan_barcode("0100202"),
            StockProductScreen.enterLotNumber("1", "lot"),
            ProductScreen.selectedOrderlineHas("Test Product 2", "1", "120.0", "Red"),

            ProductScreen.totalAmountIs("300.0"),

            refresh(),
            inLeftSide([
                ...ProductScreen.clickLine("Test Product 1"),
                ...ProductScreen.selectedOrderlineHasDirect("Test Product 1", "1"),
                Numpad.click("2"),
                ...ProductScreen.selectedOrderlineHasDirect("Test Product 1", "2", "140.0"),
            ]),

            scan_barcode("0100300"),
            ProductScreen.selectedOrderlineHas("Test Product 3", "1", "50.0"),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_only_existing_lots", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Product with existing lots"),
            StockProductScreen.selectNthLotNumber(1),
            ProductScreen.selectedOrderlineHas("Product with existing lots", "1.0"),
            inLeftSide({
                trigger: ".order-container .orderline .lot-number:contains('Lot 1001')",
            }),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_product_info_product_inventory", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            inLeftSide([
                ...scan_barcode("product_variant_0"),
                ...ProductScreen.clickControlButton("Info"),
                {
                    trigger: ".section-inventory-body :contains(100)",
                },
                Dialog.confirm("Close"),
            ]),

            inLeftSide([
                ...scan_barcode("product_variant_1"),
                ...ProductScreen.clickControlButton("Info"),
                {
                    trigger: ".section-inventory-body :contains(200)",
                },
                Dialog.confirm("Close"),
            ]),
        ].flat(),
});

registry.category("web_tour.tours").add("AddMultipleSerialsAtOnce", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Product A"),
            StockProductScreen.enterLotNumbers(["SN001", "SN002", "SN003"]),
            ProductScreen.selectedOrderlineHas("Product A", "3.0"),
            ProductScreen.clickDisplayedProduct("Product A"),
            [
                {
                    trigger: ".fa-trash-o",
                    run: "click",
                },
            ],
            StockProductScreen.enterLotNumbers(["SN005", "SN006"]),
            ProductScreen.selectedOrderlineHas("Product A", "4.0"),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("GS1BarcodeScanningTourWithLots", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // Add the Product 1 with GS1 barcode
            scan_barcode("0108431673020125100000001"),
            ProductScreen.selectedOrderlineHas("Product 1"),
            scan_barcode("0108431673020125100000001"),
            ProductScreen.selectedOrderlineHas("Product 1", 2),

            // Add the product 1 with GS1 barcode and quantity
            scan_barcode("0108431673020125305"),
            ProductScreen.selectedOrderlineHas("Product 1", 7),
            scan_barcode("01084316730201253010"),
            ProductScreen.selectedOrderlineHas("Product 1", 17),

            // Add the Product 2 with normal barcode
            scan_barcode("08431673020126"),
            ProductScreen.selectedOrderlineHas("Product 2"),
            scan_barcode("08431673020126"),
            ProductScreen.selectedOrderlineHas("Product 2", 2),

            // Add the Product 3 with normal barcode
            scan_barcode("3760171283370"),
            ProductScreen.selectedOrderlineHas("Product 3"),
            scan_barcode("3760171283370"),
            ProductScreen.selectedOrderlineHas("Product 3", 2),

            // Scanning lot number of product temoplate and variant have GS1 barcode should add the product to the order.
            scan_barcode("010512364869541610784512"),
            ProductScreen.selectedOrderlineHas("GS1 Variant Product", 1),
            Chrome.endTour(),
        ].flat(),
});
