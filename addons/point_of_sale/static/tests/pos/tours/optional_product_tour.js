import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as OptionalProduct from "@point_of_sale/../tests/pos/tours/utils/optional_product_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_optional_product", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // Select a product without configurable options
            ProductScreen.clickDisplayedProduct("Product for pricelist 5", false),
            Dialog.is({ title: "Optional Products" }),
            // Cancel the popup; no optional product should be added to the cart
            Dialog.cancel(),
            ProductScreen.selectedOrderlineHas("Product for pricelist 5", "1.0", "1.98"),

            // Add a product with optional products
            ProductScreen.clickDisplayedProduct("Product for pricelist 5", false),
            Dialog.is({ title: "Optional Products" }),
            // Add a specific optional product
            OptionalProduct.addOptionalProduct("Product for pricelist 2", 5),
            ProductScreen.selectedOrderlineHas("Product for pricelist 2", "5.0"),

            ProductScreen.clickDisplayedProduct("Product for pricelist 6"),
            // Add an optional product with configurations
            OptionalProduct.addOptionalProduct("Configurable 1", 5, true),
            // Verify the configurable product is added with correct attributes and quantity
            ProductScreen.selectedOrderlineHas("Configurable 1", "5.0", "55.0", "Blue, One, One"),
            Chrome.endTour(),
        ].flat(),
});
