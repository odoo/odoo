import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as ProductConfigurator from "@point_of_sale/../tests/pos/tours/utils/product_configurator_util";
import * as combo from "@point_of_sale/../tests/pos/tours/utils/combo_popup_util";
import * as Order from "@point_of_sale/../tests/generic_helpers/order_widget_util";
import { inLeftSide } from "@point_of_sale/../tests/pos/tours/utils/common";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("ProductConfiguratorTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // Click on Configurable Chair product
            ProductScreen.clickDisplayedProduct("Configurable Chair"),

            // Cancel configuration, not product should be in order
            Dialog.cancel(),
            ProductScreen.orderIsEmpty(),

            // Click on Configurable Chair product
            ProductScreen.clickDisplayedProduct("Configurable Chair"),

            // Pick Color
            ProductConfigurator.pickColor("Red"),

            // Pick Radio
            ProductConfigurator.pickSelect("Metal"),

            // Pick Select
            ProductConfigurator.pickRadio("Other"),

            // Fill in custom attribute
            ProductConfigurator.fillCustomAttribute("Custom Fabric"),

            // Confirm configuration
            Dialog.confirm(),

            // Check that the product has been added to the order with correct attributes and price
            ProductScreen.selectedOrderlineHas(
                "Configurable Chair",
                "1",
                "11.0",
                "Red, Metal, Fabrics: Other: Custom Fabric"
            ),

            // Orderlines with the same attributes should be merged
            ProductScreen.clickDisplayedProduct("Configurable Chair"),
            ProductConfigurator.pickColor("Red"),
            ProductConfigurator.pickSelect("Metal"),
            ProductConfigurator.pickRadio("Other"),
            ProductConfigurator.fillCustomAttribute("Custom Fabric"),
            Dialog.confirm(),
            ProductScreen.selectedOrderlineHas(
                "Configurable Chair",
                "2",
                "22.0",
                "Red, Metal, Fabrics: Other: Custom Fabric"
            ),

            // Orderlines with different attributes shouldn't be merged
            ProductScreen.clickDisplayedProduct("Configurable Chair"),
            ProductConfigurator.pickColor("Blue"),
            ProductConfigurator.pickSelect("Metal"),
            ProductConfigurator.pickRadio("Leather"),
            Dialog.confirm(),
            ProductScreen.selectedOrderlineHas(
                "Configurable Chair",
                "1",
                "10.0",
                "Blue, Metal, Leather"
            ),

            // Inactive variant attributes should not be displayed
            ProductScreen.clickDisplayedProduct("Configurable Chair"),
            // Active: Other and Leather, Inactive: Wool
            ProductConfigurator.numberRadioOptions(2),
            Dialog.confirm(),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("PosProductWithDynamicAttributes", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Dynamic Product"),
            ProductConfigurator.pickRadio("Test 1"),
            Dialog.confirm(),
            ProductScreen.selectedOrderlineHas("Dynamic Product", "1", "1.15", "Test 1"),
            ProductScreen.clickDisplayedProduct("Dynamic Product"),
            ProductConfigurator.pickRadio("Test 2"),
            Dialog.confirm(),
            ProductScreen.selectedOrderlineHas("Dynamic Product", "1", "12.65", "Test 2"),
        ].flat(),
});

registry.category("web_tour.tours").add("test_attribute_order", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Product Test"),
            ProductConfigurator.pickRadio("Value 1"),
            ProductConfigurator.pickRadio("Value 2"),
            ProductConfigurator.pickRadio("Value 3"),
            Dialog.confirm(),
            ProductScreen.selectedOrderlineHas(
                "Product Test",
                "1",
                "10",
                "Value 1, Value 2, Value 3"
            ),
        ].flat(),
});

registry.category("web_tour.tours").add("test_combo_variant_mix", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // Click on Configurable Chair product
            ProductScreen.clickDisplayedProduct("Test Product Combo"),
            combo.select("Test Product (Large)"),
            Dialog.is("Attribute selection"),
            ProductConfigurator.pickRadio("Blue"),
            Dialog.confirm("Add"),
            Dialog.confirm(),
            inLeftSide(
                [
                    Order.hasLine({
                        product: "Test Product",
                        quantity: 1,
                        price: 20.0,
                        attributes: "Blue, Large",
                    }),
                ].flat()
            ),
        ].flat(),
});
