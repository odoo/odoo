import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as ProductConfigurator from "@point_of_sale/../tests/pos/tours/utils/product_configurator_util";
import { registry } from "@web/core/registry";
import { negateStep } from "@point_of_sale/../tests/generic_helpers/utils";

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
            ProductScreen.totalAmountIs("26.40"),
            ProductScreen.clickDisplayedProduct("Configurable Product"),
            ProductConfigurator.priceIs("24.20"), // 20 (pricelist 2) + 2 (Red) + 2.2 (10% tax)
            ProductConfigurator.pickRadio("Blue"),
            ProductConfigurator.priceIs("25.30"), // 20 (pricelist 2) + 3 (Blue) + 2.3 (10% tax)
            Dialog.confirm(),
            ProductScreen.totalAmountIs("51.70"),
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

registry.category("web_tour.tours").add("test_product_with_single_value_dynamic_attribute", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ProductScreen.clickDisplayedProduct("Single Dynamic Product"),
            ProductScreen.selectedOrderlineHas("Single Dynamic Product", "1", "5.0"),

            ProductScreen.clickDisplayedProduct("Mixed Attribute Product"),
            ProductScreen.selectedOrderlineHas("Mixed Attribute Product", "1", "7.0"),
            Chrome.endTour(),
        ].flat(),
});
