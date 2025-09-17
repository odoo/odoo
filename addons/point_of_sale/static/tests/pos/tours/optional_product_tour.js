import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as OptionalProduct from "@point_of_sale/../tests/pos/tours/utils/optional_product_util";
import { registry } from "@web/core/registry";
import { scan_barcode } from "@point_of_sale/../tests/generic_helpers/utils";

registry.category("web_tour.tours").add("test_optional_product", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // Select a product without configurable options
            ProductScreen.clickDisplayedProduct("Desk Pad", false),
            Dialog.is({ title: "Optional Products" }),
            // Cancel the popup; no optional product should be added to the cart
            Dialog.cancel(),
            ProductScreen.selectedOrderlineHas("Desk Pad", "1.0", "1.98"),

            // Add a product with optional products
            ProductScreen.clickDisplayedProduct("Desk Pad", false),
            Dialog.is({ title: "Optional Products" }),
            // Add a specific optional product
            OptionalProduct.addOptionalProduct("Small Shelf", 5),
            ProductScreen.selectedOrderlineHas("Small Shelf", "5.0"),

            ProductScreen.clickDisplayedProduct("Letter Tray"),
            // Add an optional product with configurations
            OptionalProduct.addOptionalProduct("Configurable Chair", 5, true),
            // Verify the configurable product is added with correct attributes and quantity
            ProductScreen.selectedOrderlineHas(
                "Configurable Chair",
                "5.0",
                "50.0",
                "Blue, Metal, wool"
            ),

            // Scan a product with optional products
            scan_barcode("lettertray"),
            Dialog.is({ title: "Optional Products" }),
            // Add an optional product
            OptionalProduct.addOptionalProduct("Configurable Chair", 2, true),
            // Verify the configurable product is added with correct attributes and quantity
            ProductScreen.selectedOrderlineHas(
                "Configurable Chair",
                "7.0",
                "70.0",
                "Blue, Metal, wool"
            ),

            Chrome.endTour(),
        ].flat(),
});
