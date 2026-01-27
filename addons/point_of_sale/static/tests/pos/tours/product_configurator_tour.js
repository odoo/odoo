import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as ProductConfigurator from "@point_of_sale/../tests/pos/tours/utils/product_configurator_util";
import * as combo from "@point_of_sale/../tests/pos/tours/utils/combo_popup_util";
import * as Order from "@point_of_sale/../tests/generic_helpers/order_widget_util";
import { inLeftSide } from "@point_of_sale/../tests/pos/tours/utils/common";
import { registry } from "@web/core/registry";
import { negateStep } from "@point_of_sale/../tests/generic_helpers/utils";

registry.category("web_tour.tours").add("ProductConfiguratorTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // Click on Configurable Chair product
            ProductScreen.clickDisplayedProduct("Configurable Chair"),
            ProductConfigurator.selectedColor("Red"),
            ProductConfigurator.selectedSelect("Metal"),
            ProductConfigurator.selectedRadio("Leather"),

            // Cancel configuration, not product should be in order
            Dialog.cancel(),
            ProductScreen.orderIsEmpty(),

            // Click on Configurable Chair product
            ProductScreen.clickDisplayedProduct("Configurable Chair"),

            // Select attributes
            ProductConfigurator.pickRadio("Other"),
            ProductConfigurator.fillCustomAttribute("Custom Fabric"),
            ProductConfigurator.pickMulti("Cushion"),
            ProductConfigurator.pickMulti("Headrest"),

            ProductConfigurator.selectedColor("Red"),
            ProductConfigurator.selectedSelect("Metal"),
            ProductConfigurator.selectedRadio("Other"),
            ProductConfigurator.selectedCustomAttribute("Custom Fabric"),
            ProductConfigurator.selectedMulti("Cushion"),
            ProductConfigurator.selectedMulti("Headrest"),

            // Check that the product has been added to the order with correct attributes and price
            Dialog.confirm(),
            ProductScreen.selectedOrderlineHas(
                "Configurable Chair",
                "1",
                "11.0",
                "Red, Metal, Fabrics: Other: Custom Fabric, Cushion, Headrest"
            ),

            // Orderlines with the same attributes should be merged
            ProductScreen.clickDisplayedProduct("Configurable Chair"),
            ProductConfigurator.pickRadio("Other"),
            ProductConfigurator.fillCustomAttribute("Custom Fabric"),
            ProductConfigurator.pickMulti("Cushion"),
            ProductConfigurator.pickMulti("Headrest"),
            Dialog.confirm(),
            ProductScreen.selectedOrderlineHas(
                "Configurable Chair",
                "2",
                "22.0",
                "Red, Metal, Fabrics: Other: Custom Fabric, Cushion, Headrest"
            ),

            // Orderlines with different attributes shouldn't be merged
            ProductScreen.clickDisplayedProduct("Configurable Chair"),
            ProductConfigurator.pickColor("Blue"),
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
            Dialog.cancel(),

            // Reopen configuration and discard changes --> Come back to previous attributes
            ProductScreen.openCartMobile(),
            ProductScreen.longPressOrderline("Configurable Chair"),
            ProductConfigurator.selectedColor("Red"),
            ProductConfigurator.selectedSelect("Metal"),
            ProductConfigurator.selectedRadio("Other"),
            ProductConfigurator.selectedCustomAttribute("Custom Fabric"),
            ProductConfigurator.selectedMulti("Cushion"),
            ProductConfigurator.selectedMulti("Headrest"),

            ProductConfigurator.pickColor("Blue"),
            ProductConfigurator.fillCustomAttribute("Azerty"),
            Dialog.cancel(),
            ProductScreen.clickLine("Configurable Chair", 2),
            ProductScreen.selectedOrderlineHasDirect(
                "Configurable Chair",
                "2",
                "22.0",
                "Red, Metal, Fabrics: Other: Custom Fabric, Cushion, Headrest"
            ),
        ].flat(),
});

registry.category("web_tour.tours").add("PosProductWithDynamicAttributes", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.searchProduct("Non Existing Product"),
            ProductScreen.productIsDisplayed("Dynamic Product").map(negateStep),
            ProductScreen.searchProduct("Dynamic Product"),
            ProductScreen.productIsDisplayed("Dynamic Product"),
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

registry.category("web_tour.tours").add("test_cross_exclusion_attribute_values", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Test Product 1"),
            ProductConfigurator.pickRadio("attribute_1_value_1"),
            [
                {
                    content: `check radio attribute with name attribute_2_value_1 is muted`,
                    trigger: `.modal .attribute-name-cell:contains('attribute_2_value_1') span.text-muted`,
                },
            ],
            ProductConfigurator.pickRadio("attribute_2_value_1"),
            ProductConfigurator.isAddDisabled(),
            ProductConfigurator.pickRadio("attribute_2_value_2"),
            [
                {
                    content: `check radio attribute with name attribute_1_value_2 is muted`,
                    trigger: `.modal .attribute-name-cell:contains('attribute_1_value_2') span.text-muted`,
                },
            ],
            ProductConfigurator.pickRadio("attribute_1_value_2"),
            ProductConfigurator.isAddDisabled(),
            ProductConfigurator.pickRadio("attribute_1_value_1"),
            ProductConfigurator.pickRadio("attribute_2_value_2"),
            ProductConfigurator.isAddEnabled(),
            ProductConfigurator.pickRadio("attribute_1_value_2"),
            ProductConfigurator.pickRadio("attribute_2_value_1"),
            ProductConfigurator.isAddEnabled(),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_exclusion_attribute_values", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Configurable Chair"),
            ProductConfigurator.pickColor("Red"),
            ProductConfigurator.pickSelect("Metal"),
            ProductConfigurator.isUnavailable("Other"),
            ProductConfigurator.isUnavailable("Wool"),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_custom_attribute_alone_displayed", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Only Custom"),
            ProductConfigurator.fillCustomAttribute("Filling"),
            ProductConfigurator.selectedCustomAttribute("Filling"),
            Dialog.confirm(),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_product_configurator_price", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Configurable Product"),
            ProductConfigurator.priceIs("13.20"), // 10 (Small) + 2 (Red) + 1.2 (10% tax)
            ProductConfigurator.pickRadio("Large"),
            ProductConfigurator.priceIs("14.30"), // 10 + 1 (Large) + 2 (Red) + 1.3 (10% tax)
            ProductConfigurator.pickRadio("Blue"),
            ProductConfigurator.priceIs("15.40"), // 10 + 1 (Large) + 3 (Blue) + 1.4 (10% tax)
            Dialog.confirm(),
            ProductScreen.totalAmountIs("15.40"),
            ProductScreen.clickPriceList("Pricelist 2"),
            ProductScreen.totalAmountIs("22.00"),
            ProductScreen.clickDisplayedProduct("Configurable Product"),
            ProductConfigurator.priceIs("22.00"), // 20 (pricelist 2) + 2 (10% tax)
            ProductConfigurator.pickRadio("Blue"),
            ProductConfigurator.priceIs("22.00"), // 20 (pricelist 2) + 2 (10% tax)
            Dialog.confirm(),
            ProductScreen.totalAmountIs("44.00"),
            Chrome.createFloatingOrder(),
            ProductScreen.clickFiscalPosition("Include to Exclude"),
            ProductScreen.clickDisplayedProduct("Configurable Product"),
            ProductConfigurator.priceIs("12.00"), // 10 (Small) + 2 (Red)
            ProductConfigurator.pickRadio("Large"),
            ProductConfigurator.priceIs("13.00"), // 10 + 1 (Large) + 2 (Red)
            ProductConfigurator.pickRadio("Blue"),
            ProductConfigurator.priceIs("14.00"), // 10 + 1 (Large) + 3 (Blue)
            Dialog.confirm(),
            ProductScreen.totalAmountIs("14.00"),
            Chrome.endTour(),
        ].flat(),
});
