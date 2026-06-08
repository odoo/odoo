import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as combo from "@point_of_sale/../tests/pos/tours/utils/combo_popup_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import { refresh } from "@point_of_sale/../tests/generic_helpers/utils";
import { inLeftSide } from "@point_of_sale/../tests/pos/tours/utils/common";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import { registry } from "@web/core/registry";
import * as ProductConfigurator from "@point_of_sale/../tests/pos/tours/utils/product_configurator_util";

const setupProductConfigurator = [
    ProductConfigurator.pickColor("Blue"),
    ProductConfigurator.pickSelect("Wood"),
    ProductConfigurator.pickRadio("Other"),
    ProductConfigurator.fillCustomAttribute("Azerty"),
    ProductConfigurator.pickMulti("Cushion"),
    ProductConfigurator.pickMulti("Headrest"),
].flat();

const checkProductConfigurator = [
    ProductConfigurator.selectedColor("Blue"),
    ProductConfigurator.selectedSelect("Wood"),
    ProductConfigurator.selectedRadio("Other"),
    ProductConfigurator.selectedCustomAttribute("Azerty"),
    ProductConfigurator.selectedMulti("Cushion"),
    ProductConfigurator.selectedMulti("Headrest"),
].flat();

const checkConfiguredLine = (isCombo = false) => {
    const method = isCombo ? ProductScreen.orderComboLineHas : ProductScreen.orderLineHas;
    return [
        method(
            "Configurable Chair",
            "1.0",
            "",
            "Blue, Wood, Fabrics: Other: Azerty, Cushion, Headrest"
        ),
    ].flat();
};

registry.category("web_tour.tours").add("test_line_configurators_product", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ProductScreen.clickDisplayedProduct("Configurable Chair"),
            ...setupProductConfigurator,
            Dialog.confirm(),

            inLeftSide([
                ...ProductScreen.longPressOrderline("Configurable Chair"),
                Dialog.discard(),
                ...checkConfiguredLine(false),
                ...ProductScreen.longPressOrderline("Configurable Chair"),
                ...checkProductConfigurator,
                Dialog.confirm(),
                ...checkConfiguredLine(false),
            ]),
            refresh(),
            inLeftSide([
                ...checkConfiguredLine(false),
                ...ProductScreen.longPressOrderline("Configurable Chair"),
                ...checkProductConfigurator,
                Dialog.discard(),
                ...checkConfiguredLine(false),
            ]),
        ].flat(),
});

registry.category("web_tour.tours").add("test_line_configurators_combo", {
    steps: () =>
        [
            Chrome.startPoS(),
            ProductScreen.clickDisplayedProduct("Office Combo"),
            // Select first combo (combo 1)
            combo.select("Combo Product 2"),
            combo.isSelected("Combo Product 2"),

            // Open Product Configurator + Configure + Confirm (combo 2)
            combo.select("Configurable Chair"),
            ...setupProductConfigurator,
            Dialog.confirm(),

            // Select it again
            combo.select("Configurable Chair"),
            ...setupProductConfigurator,
            Dialog.confirm(),

            // Select last combo (combo 3)
            combo.select("Combo Product 6"),
            combo.isSelected("Combo Product 6"),
            Dialog.confirm(),

            inLeftSide([
                ...ProductScreen.orderComboLineHas("Combo Product 2", "1.0"),
                ...checkConfiguredLine(true),
                ...ProductScreen.orderComboLineHas("Combo Product 6", "1.0"),

                // Edit combo
                ...ProductScreen.longPressOrderline("Office Combo"),
                combo.isSelected("Combo Product 2"),
                combo.isSelected("Configurable Chair"),
                combo.isSelected("Combo Product 6"),
                Dialog.confirm("Add to Order"),

                ...ProductScreen.orderComboLineHas("Combo Product 2", "1.0"),
                ...checkConfiguredLine(true),
                ...ProductScreen.orderComboLineHas("Combo Product 6", "1.0"),
            ]),
            refresh(),
            inLeftSide([
                ...ProductScreen.longPressOrderline("Office Combo"),
                combo.isSelected("Combo Product 2"),
                combo.isSelected("Configurable Chair"),
                combo.isSelected("Combo Product 6"),

                combo.select("Configurable Chair"),
                ...checkProductConfigurator,
                Dialog.confirm(),
                Dialog.confirm("Add to Order"),

                ...ProductScreen.orderComboLineHas("Combo Product 2", "1.0"),
                ...checkConfiguredLine(true),
                ...ProductScreen.orderComboLineHas("Combo Product 6", "1.0"),

                ...ProductScreen.longPressOrderline("Office Combo"),
                Dialog.cancel(),
                ...ProductScreen.longPressOrderline("Office Combo"),
                combo.isSelected("Configurable Chair"),
                Dialog.confirm("Add to Order"),
            ]),
        ].flat(),
});
