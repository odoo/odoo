/* global posmodel */

import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";
import * as combo from "@point_of_sale/../tests/pos/tours/utils/combo_popup_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as Order from "@point_of_sale/../tests/generic_helpers/order_widget_util";
import { scan_barcode } from "@point_of_sale/../tests/generic_helpers/utils";
import { inLeftSide } from "@point_of_sale/../tests/pos/tours/utils/common";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import { registry } from "@web/core/registry";
import * as Numpad from "@point_of_sale/../tests/generic_helpers/numpad_util";

registry.category("web_tour.tours").add("ProductComboPriceTaxIncludedTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ...ProductScreen.clickDisplayedProduct("Sofa Combo"),
            combo.select("Combo Product Sofa (L)"),
            Dialog.confirm(),
            inLeftSide([
                ...Order.hasLine({
                    withoutClass: ".selected",
                    productName: "Combo Product Sofa",
                    run: "click",
                    quantity: "1",
                    attributeLine: "L",
                    priceUnit: 34.5,
                }),
                Numpad.click("⌫"),
                Numpad.click("⌫"),
                ...Order.doesNotHaveLine(),
            ]),
            scan_barcode("SuperCombo"),
            combo.select("Combo Product 3"),
            combo.isConfirmationButtonDisabled(),
            combo.select("Combo Product 9"),
            // Check Product Configurator is open
            Dialog.is("Attribute selection"),
            {
                content: "dialog discard",
                trigger:
                    ".modal-footer .o-default-button:text(Add) + .o-default-button:text(Discard)",
                run: "click",
            },
            combo.select("Combo Product 5"),
            combo.select("Combo Product 7"),
            combo.isSelected("Combo Product 7"),
            combo.select("Combo Product 8"),
            combo.isSelected("Combo Product 8"),
            combo.isNotSelected("Combo Product 7"),
            Dialog.confirm(),
            inLeftSide([
                ...ProductScreen.selectedOrderlineHasDirect("Office Combo", "1", "62.1"),
                ...ProductScreen.clickLine("Combo Product 3"),
                ...ProductScreen.selectedOrderlineHasDirect("Combo Product 3", "1"),
                ...ProductScreen.clickLine("Combo Product 5"),
                ...ProductScreen.selectedOrderlineHasDirect("Combo Product 5", "1"),
                ...ProductScreen.clickLine("Combo Product 8"),
                ...ProductScreen.selectedOrderlineHasDirect("Combo Product 8", "1"),
            ]),
            // check that you can select a customer which triggers a recomputation of the price
            ...ProductScreen.clickPartnerButton(),
            ...ProductScreen.clickCustomer("Partner Test 1"),

            // check that you can change the quantity of a combo product
            inLeftSide([
                ...ProductScreen.clickLine("Combo Product 3"),
                Numpad.click("2"),
                ...ProductScreen.selectedOrderlineHasDirect("Combo Product 3", "2"),
                ...ProductScreen.orderLineHas("Combo Product 5", "2"),
                ...ProductScreen.orderLineHas("Combo Product 8", "2"),
                ...ProductScreen.orderLineHas("Office Combo", "2", "124.2"),
            ]),

            // check that removing a combo product removes all the combo products
            inLeftSide([
                {
                    ...ProductScreen.clickLine("Combo Product 3", "2")[0],
                    isActive: ["mobile"],
                },
                Numpad.click("⌫"),
                Numpad.click("⌫"),
                ...Order.doesNotHaveLine(),
            ]),

            ...ProductScreen.clickDisplayedProduct("Office Combo"),
            combo.select("Combo Product 3"),
            combo.select("Combo Product 5"),
            combo.select("Combo Product 8"),
            Dialog.confirm(),
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
            Dialog.confirm(),
            {
                content: "The 'Combo Product 6' card should not display a quantity.",
                trigger:
                    "article.product .product-content:has(.product-name:contains('Combo Product 6')):not(:has(.product-cart-qty))",
            },
            ...ProductScreen.totalAmountIs("59.17"),
            ...inLeftSide(Order.hasTax("10.56")),
            // the split screen is tested in `pos_restaurant`
        ].flat(),
});

registry.category("web_tour.tours").add("ProductComboPriceCheckTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Desk Combo"),
            inLeftSide([
                ...ProductScreen.selectedOrderlineHasDirect("Desk Combo", "1", "7.00"),
                ...ProductScreen.orderLineHas("Desk Organizer", "1"),
                ...ProductScreen.orderLineHas("Desk Pad", "1"),
                ...ProductScreen.orderLineHas("Whiteboard Pen", "1"),
            ]),
            ProductScreen.totalAmountIs("7.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("ProductComboChangeFP", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ProductScreen.clickDisplayedProduct("Office Combo"),
            ProductScreen.checkProductExtraPrice("Combo Product 3", "2"),
            combo.select("Combo Product 2"),
            combo.select("Combo Product 4"),
            combo.select("Combo Product 6"),
            Dialog.confirm(),

            inLeftSide([...ProductScreen.orderLineHas("Office Combo", "1", "50.00")]),
            ProductScreen.totalAmountIs("50.00"),
            inLeftSide(Order.hasTax("4.55")),

            // Test than changing the fp, doesn't change the price of the combo
            ProductScreen.clickFiscalPosition("test fp"),
            inLeftSide([...ProductScreen.orderLineHas("Office Combo", "1", "50.00")]),
            ProductScreen.totalAmountIs("50.00"),
            inLeftSide(Order.hasTax("2.38")),
            ProductScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("ProductComboChangePricelist", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Office Combo"),
            combo.select("Combo Product 2"),
            combo.select("Combo Product 4"),
            combo.select("Combo Product 6"),
            Dialog.confirm(),
            inLeftSide([
                ...ProductScreen.orderComboLineHas("Combo Product 2", "1.0", "6.67"),
                ...ProductScreen.orderComboLineHas("Combo Product 4", "1.0", "14.66"),
                ...ProductScreen.orderComboLineHas("Combo Product 6", "1.0", "26.00"),
            ]),
            ProductScreen.totalAmountIs("47.33"),
            ProductScreen.clickPriceList("sale 10%"),
            inLeftSide([
                ...ProductScreen.orderComboLineHas("Combo Product 2", "1.0", "6.00"),
                ...ProductScreen.orderComboLineHas("Combo Product 4", "1.0", "13.20"),
                ...ProductScreen.orderComboLineHas("Combo Product 6", "1.0", "23.40"),
            ]),
            ProductScreen.totalAmountIs("42.60"),
            ProductScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_combo_disallowLineQuantityChange", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
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
            Dialog.confirm(),
            inLeftSide(
                [
                    Numpad.click("⌫"),
                    {
                        content: "Click 0",
                        trigger:
                            ".modal-content div.numpad button:not(:contains('+')):contains('0')",
                        run: "click",
                    },
                    Chrome.confirmPopup(),
                    Order.doesNotHaveLine(),
                ].flat()
            ),
        ].flat(),
});

registry.category("web_tour.tours").add("test_combo_disallowLineQuantityChange_2", {
    steps: () =>
        [
            Chrome.startPoS(),
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
            Dialog.confirm(),
            inLeftSide(
                [
                    Numpad.click("2"),
                    {
                        content: "Click 2",
                        trigger:
                            ".modal-content div.numpad button:not(:contains('+')):contains('2')",
                        run: "click",
                    },
                    Chrome.confirmPopup(),
                    Order.hasLine({ productName: "Combo Product 2", quantity: "2" }),
                    Order.hasLine({ productName: "Combo Product 4", quantity: "2" }),
                    Order.hasLine({ productName: "Combo Product 6", quantity: "2" }),
                    Numpad.click("1"),
                    {
                        content: "Click 1",
                        trigger:
                            ".modal-content div.numpad button:not(:contains('+')):contains('1')",
                        run: "click",
                    },
                    Chrome.confirmPopup(),
                    Order.hasLine({ productName: "Combo Product 2", quantity: "1" }),
                    Order.hasLine({ productName: "Combo Product 4", quantity: "1" }),
                    Order.hasLine({ productName: "Combo Product 6", quantity: "1" }),
                ].flat()
            ),
            Order.hasTotal("47.33"),
        ].flat(),
});

registry.category("web_tour.tours").add("test_combo_item_image_display", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Office Combo"),
            combo.checkImgAndSelect("Combo Product 2", true),
            combo.checkImgAndSelect("Combo Product 4", true),
            combo.checkImgAndSelect("Combo Product 6", true),
            Dialog.confirm(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_combo_item_image_not_display", {
    steps: () =>
        [
            Chrome.startPoS(),
            ProductScreen.clickDisplayedProduct("Office Combo"),
            combo.checkImgAndSelect("Combo Product 2", false),
            combo.checkImgAndSelect("Combo Product 4", false),
            combo.checkImgAndSelect("Combo Product 6", false),
            Dialog.confirm(),
        ].flat(),
});
