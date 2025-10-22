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
import * as Utils from "@point_of_sale/../tests/generic_helpers/utils";

registry.category("web_tour.tours").add("ProductComboPriceTaxIncludedTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            scan_barcode("SuperCombo"),
            combo.select("Combo Product 3"),
            combo.isConfirmationButtonDisabled(),
            combo.select("Combo Product 9"),
            // Check Product Configurator is open
            Dialog.is("Attribute selection"),
            {
                content: "dialog discard",
                trigger: ".modal-footer .btn:contains(/^Add$/) + .btn:contains(/^Discard$/)",
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

registry.category("web_tour.tours").add("ProductComboMaxFreeQtyTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // Desk accessories combo
            ProductScreen.clickDisplayedProduct("Office Combo"),
            combo.checkTotal("40.00"),
            combo.select("Combo Product 3"),
            combo.checkTotal("42.00"),

            // Desks combo
            combo.select("Combo Product 5"),
            combo.checkProductQty("Combo Product 5", "1"),
            combo.select("Combo Product 5"),
            combo.select("Combo Product 5"),
            // Check that we cannot exceed the combo 'max_qty' which is 2
            combo.checkProductQty("Combo Product 5", "2"),
            combo.checkTotal("46.00"),
            combo.clickQtyBtnMinus("Combo Product 5"),
            combo.checkProductQty("Combo Product 5", "1"),
            combo.select("Combo Product 4"),
            combo.checkProductQty("Combo Product 4", "1"),
            combo.checkTotal("44.00"),
            combo.isConfirmationButtonDisabled(),

            // Chairs combo
            combo.select("Combo Product 6"),
            combo.clickQtyBtnAdd("Combo Product 6"),
            combo.checkProductQty("Combo Product 6", "2"),
            // Confirmation should be enabled as we have selected the "min" qty for each combo
            Utils.negateStep(combo.isConfirmationButtonDisabled()),
            // As for chairs combo : 'qty_max' > 'qty_free', we can still select the product, but we'll pay them as extra (combo 'base_price')
            combo.checkTotal("44.00"),
            combo.select("Combo Product 7"),
            combo.clickQtyBtnAdd("Combo Product 7"),
            combo.clickQtyBtnAdd("Combo Product 7"),
            combo.checkProductQty("Combo Product 7", "3"),
            combo.checkTotal("134.00"),

            Dialog.confirm(),
            inLeftSide([
                ...ProductScreen.selectedOrderlineHasDirect("Office Combo", "1", "151.98"),
            ]),
            ProductScreen.totalAmountIs("151.98"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
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
                ...ProductScreen.orderComboLineHas("Combo Product 2", "1.0"),
                ...ProductScreen.orderComboLineHas("Combo Product 4", "1.0"),
                ...ProductScreen.orderComboLineHas("Combo Product 6", "1.0"),
            ]),
            ProductScreen.totalAmountIs("47.33"),
            ProductScreen.clickPriceList("sale 10%"),
            inLeftSide([
                ...ProductScreen.orderComboLineHas("Combo Product 2", "1.0"),
                ...ProductScreen.orderComboLineHas("Combo Product 4", "1.0"),
                ...ProductScreen.orderComboLineHas("Combo Product 6", "1.0"),
            ]),
            ProductScreen.totalAmountIs("42.60"),
            ProductScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("ProductComboDiscountTour", {
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
            inLeftSide([Numpad.click("%"), Numpad.click("2"), Numpad.click("0")]),
            ProductScreen.totalAmountIs("80.00"),
            ProductScreen.isShown(),
        ].flat(),
});
