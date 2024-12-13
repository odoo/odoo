import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";
import * as combo from "@point_of_sale/../tests/pos/tours/utils/combo_popup_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as Order from "@point_of_sale/../tests/generic_helpers/order_widget_util";
import { inLeftSide } from "@point_of_sale/../tests/pos/tours/utils/common";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import { registry } from "@web/core/registry";
import * as Numpad from "@point_of_sale/../tests/generic_helpers/numpad_util";

registry.category("web_tour.tours").add("ProductComboPriceTaxIncludedTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ...ProductScreen.clickDisplayedProduct("Office Combo"),
            combo.select("Combo Product 3"),
            combo.isConfirmationButtonDisabled(),
            combo.select("Combo Product 9"),
            // Check Product Configurator is open
            Dialog.is("Attribute selection"),
            Dialog.discard(),
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
