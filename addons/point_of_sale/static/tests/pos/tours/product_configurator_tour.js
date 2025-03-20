import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as ProductConfigurator from "@point_of_sale/../tests/pos/tours/utils/product_configurator_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("ProductConfiguratorTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Configurable 1"),
            Dialog.cancel(),
            ProductScreen.orderIsEmpty(),
            ProductScreen.clickDisplayedProduct("Configurable 1"),
            ProductConfigurator.pickColor("Red"),
            ProductConfigurator.pickSelect("One"),
            ProductConfigurator.pickRadio("Custom"),
            ProductConfigurator.fillCustomAttribute("Custom Fabric"),
            Dialog.confirm(),
            ProductScreen.selectedOrderlineHas(
                "Configurable 1",
                "1",
                "11.0",
                "Red, One, Radio: Custom: Custom Fabric"
            ),
            // Orderlines with the same attributes should be merged
            ProductScreen.clickDisplayedProduct("Configurable 1"),
            ProductConfigurator.pickColor("Red"),
            ProductConfigurator.pickSelect("One"),
            ProductConfigurator.pickRadio("Custom"),
            ProductConfigurator.fillCustomAttribute("Custom Fabric"),
            Dialog.confirm(),
            ProductScreen.selectedOrderlineHas(
                "Configurable 1",
                "2",
                "22.0",
                "Red, One, Radio: Custom: Custom Fabric"
            ),

            // Orderlines with different attributes shouldn't be merged
            ProductScreen.clickDisplayedProduct("Configurable 1"),
            ProductConfigurator.pickColor("Blue"),
            ProductConfigurator.pickSelect("One"),
            ProductConfigurator.pickRadio("One"),
            Dialog.confirm(),
            ProductScreen.selectedOrderlineHas("Configurable 1", "1", "11.0", "Blue, One, One"),

            // Inactive variant attributes should not be displayed
            ProductScreen.clickDisplayedProduct("Configurable 1"),
            // Active: Custom and One, Inactive: Wool
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
            ProductScreen.clickDisplayedProduct("Configurable Dynamic"),
            ProductConfigurator.pickRadio("Dynamic 1"),
            Dialog.confirm(),
            ProductScreen.selectedOrderlineHas("Configurable Dynamic", "1", "1.15", "Dynamic 1"),
            ProductScreen.clickDisplayedProduct("Configurable Dynamic"),
            ProductConfigurator.pickRadio("Dynamic 2"),
            Dialog.confirm(),
            ProductScreen.selectedOrderlineHas("Configurable Dynamic", "1", "12.65", "Dynamic 2"),
        ].flat(),
});
