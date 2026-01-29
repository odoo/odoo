/** @odoo-module */
/* global posmodel */

import * as ProductScreen from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import * as PaymentScreen from "@point_of_sale/../tests/tours/helpers/PaymentScreenTourMethods";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/helpers/ReceiptScreenTourMethods";
import * as combo from "@point_of_sale/../tests/tours/helpers/ComboPopupMethods";
import * as Order from "@point_of_sale/../tests/tours/helpers/generic_components/OrderWidgetMethods";
import * as ProductConfigurator from "@point_of_sale/../tests/tours/helpers/ProductConfiguratorTourMethods";
import * as Numpad from "@point_of_sale/../tests/tours/helpers/NumpadTourMethods";
import * as Chrome from "@point_of_sale/../tests/tours/helpers/ChromeTourMethods";
import { inLeftSide } from "@point_of_sale/../tests/tours/helpers/utils";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("PosComboPriceTaxIncludedTour", {
    test: true,
    url: "/pos/ui",
    steps: () => [
        ...ProductScreen.confirmOpeningPopup(),
        ...ProductScreen.clickDisplayedProduct("Office Combo"),
        combo.isPopupShown(),
        combo.isNotPresent("Combo Product 1"),
        combo.select("Combo Product 3"),
        combo.select("Combo Product 9"),
        ...ProductConfigurator.isShown(),
        ...ProductConfigurator.cancelAttributes(),
        {
            content: "check that amount is not displayed if zero",
            trigger: `article.product .product-content:not(:has(.price-tag:contains("0")))`,
            isCheck: true,
        },
        {
            content: "check that amount is properly displayed when it is not 0",
            trigger: `article.product .product-content .product-name:contains("Combo Product 3") ~.price-tag:contains("2.60")`,
            isCheck: true,
        },
        combo.isConfirmationButtonDisabled(),
        combo.select("Combo Product 5"),
        combo.select("Combo Product 7"),
        combo.isSelected("Combo Product 7"),
        combo.select("Combo Product 8"),
        combo.isSelected("Combo Product 8"),
        combo.isNotSelected("Combo Product 7"),
        combo.confirm(),
        ...ProductScreen.selectedOrderlineHas("Office Combo"),
        ...ProductScreen.clickOrderline("Combo Product 3"),
        ...ProductScreen.selectedOrderlineHas("Combo Product 3", "1.0", "13.43"),
        ...ProductScreen.clickOrderline("Combo Product 5"),
        ...ProductScreen.selectedOrderlineHas("Combo Product 5", "1.0", "18.67"),
        ...ProductScreen.clickOrderline("Combo Product 8"),
        ...ProductScreen.selectedOrderlineHas("Combo Product 8", "1.0", "30.00"),

        // check that there is no price shown on the parent line
        ...inLeftSide(Order.doesNotHaveLine({productName: "Office Combo", price: "0.0"})),

        // check that you can change the quantity of a combo product
        ...ProductScreen.pressNumpad("2"),
        ...ProductScreen.clickOrderline("Combo Product 3", "2.0"),
        ...ProductScreen.selectedOrderlineHas("Combo Product 3", "2.0", "26.86"),
        ...ProductScreen.clickOrderline("Combo Product 5", "2.0"),
        ...ProductScreen.selectedOrderlineHas("Combo Product 5", "2.0", "37.34"),
        ...ProductScreen.clickOrderline("Combo Product 8", "2.0"),
        ...ProductScreen.selectedOrderlineHas("Combo Product 8", "2.0", "60.00"),

        // check that removing a combo product removes all the combo products
        ...ProductScreen.pressNumpad("⌫"),
        ...ProductScreen.pressNumpad("⌫"),
        ...ProductScreen.orderIsEmpty(),

        ...ProductScreen.clickDisplayedProduct("Office Combo"),
        combo.select("Combo Product 3"),
        combo.select("Combo Product 5"),
        combo.select("Combo Product 8"),
        combo.confirm(),
        ...ProductScreen.totalAmountIs("62.10"),
        ...ProductScreen.clickPayButton(),
        ...PaymentScreen.clickPaymentMethod("Bank"),
        ...PaymentScreen.clickValidate(),
        ...ReceiptScreen.isShown(),
        ...ReceiptScreen.clickNextOrder(),

        // another order but won't be sent to the backend
        ...ProductScreen.clickDisplayedProduct("Office Combo"),
        combo.select("Combo Product 2"),
        combo.select("Combo Product 4"),
        combo.select("Combo Product 6"),
        combo.confirm(),
        ...ProductScreen.totalAmountIs("59.17"),
        ...inLeftSide(Order.hasTax("10.56")),
        // the split screen is tested in `pos_restaurant`
    ],
});

registry.category("web_tour.tours").add("PosComboChangeFP", {
    test: true,
    steps: () => [
        ProductScreen.confirmOpeningPopup(),

        ProductScreen.clickDisplayedProduct("Office Combo"),
        combo.select("Combo Product 2"),
        combo.select("Combo Product 4"),
        combo.select("Combo Product 6"),
        combo.confirm(),

        ProductScreen.selectedOrderlineHas("Office Combo"),
        ProductScreen.clickOrderline("Combo Product 2"),
        ProductScreen.selectedOrderlineHas("Combo Product 2", "1.0", "8.33"),
        ProductScreen.clickOrderline("Combo Product 4"),
        ProductScreen.selectedOrderlineHas("Combo Product 4", "1.0", "16.67"),
        ProductScreen.clickOrderline("Combo Product 6"),
        ProductScreen.selectedOrderlineHas("Combo Product 6", "1.0", "25.00"),
        ProductScreen.totalAmountIs("50.00"),
        inLeftSide(Order.hasTax("4.55")),

        // Test than changing the fp, doesn't change the price of the combo
        ProductScreen.changeFiscalPosition("test fp"),
        ProductScreen.clickOrderline("Office Combo"),
        ProductScreen.selectedOrderlineHas("Office Combo"),
        ProductScreen.clickOrderline("Combo Product 2"),
        ProductScreen.selectedOrderlineHas("Combo Product 2", "1.0", "8.33"),
        ProductScreen.clickOrderline("Combo Product 4"),
        ProductScreen.selectedOrderlineHas("Combo Product 4", "1.0", "16.67"),
        ProductScreen.clickOrderline("Combo Product 6"),
        ProductScreen.selectedOrderlineHas("Combo Product 6", "1.0", "25.00"),
        ProductScreen.totalAmountIs("50.00"),
        inLeftSide(Order.hasTax("2.38")),
        ProductScreen.isShown(),
    ].flat(),
});

registry.category("web_tour.tours").add("test_combo_with_custom_attribute", {
    test: true,
    steps: () => [
        ProductScreen.confirmOpeningPopup(),
        ProductScreen.clickDisplayedProduct("Custom Attr Combo"),
        combo.select("Custom Attr Product"),
        ProductConfigurator.fillCustomAttribute("asf"),
        ProductConfigurator.confirmAttributes(),
        combo.confirm(),
        ...inLeftSide(Order.hasLine({productName: "Custom Attr Product (Custom Value: asf)"})),
        ProductScreen.isShown(),
    ].flat(),
});

registry.category("web_tour.tours").add("test_combo_disallowLineQuantityChange", {
    steps: () =>
        [
            {
                content: "replace disallowLineQuantityChange to be true",
                trigger: "body",
                run: () => {
                    posmodel.disallowLineQuantityChange = () => true;
                },
            },
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.clickDisplayedProduct("Office Combo"),
            combo.select("Combo Product 2"),
            combo.select("Combo Product 4"),
            combo.select("Combo Product 6"),
            combo.confirm(),
            inLeftSide([
                Numpad.click("⌫"),
                {
                    content: "Click 0",
                    trigger: ".popup div.numpad.row button.col:not(:contains('+')):contains('0')",
                    run: "click",
                    mobile: false,
                },
                {
                    content: "Validate the popup",
                    trigger: ".payment-input-number",
                    run: "text 0",
                    mobile: true,
                },
                ...Chrome.confirmPopup(),
                ...Order.doesNotHaveLine(),
            ]),
        ].flat(),
});

registry.category("web_tour.tours").add("test_combo_disallowLineQuantityChange_2", {
    steps: () =>
        [
            {
                content: "replace disallowLineQuantityChange to be true",
                trigger: "body",
                run: () => {
                    posmodel.disallowLineQuantityChange = () => true;
                },
            },
            ProductScreen.clickDisplayedProduct("Office Combo"),
            combo.select("Combo Product 2"),
            combo.select("Combo Product 4"),
            combo.select("Combo Product 6"),
            combo.confirm(),
            inLeftSide([
                Numpad.click("2"),
                {
                    content: "Click 2",
                    trigger: ".popup div.numpad.row button.col:not(:contains('+')):contains('2')",
                    run: "click",
                    mobile: false,
                },
                {
                    content: "Validate the popup",
                    trigger: ".payment-input-number",
                    run: "text 2",
                    mobile: true,
                },
                ...Chrome.confirmPopup(),
                Order.hasTotal("94.67"),
                ...Order.hasLine({ productName: "Combo Product 2", quantity: "2" }),
                ...Order.hasLine({ productName: "Combo Product 4", quantity: "2" }),
                ...Order.hasLine({ productName: "Combo Product 6", quantity: "2" }),
            ]),
        ].flat(),
});
