import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/utils/receipt_screen_util";
import * as combo from "@point_of_sale/../tests/tours/utils/combo_popup_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as Order from "@point_of_sale/../tests/tours/utils/generic_components/order_widget_util";
import { inLeftSide } from "@point_of_sale/../tests/tours/utils/common";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("ProductComboPriceTaxIncludedTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ...ProductScreen.clickDisplayedProduct("Office Combo"),
            combo.select("Combo Product 3"),
            combo.isConfirmationButtonDisabled(),
            combo.select("Combo Product 5"),
            combo.select("Combo Product 7"),
            combo.isSelected("Combo Product 7"),
            combo.select("Combo Product 8"),
            combo.isSelected("Combo Product 8"),
            combo.isNotSelected("Combo Product 7"),
            Dialog.confirm(),
            ...ProductScreen.selectedOrderlineHas("Office Combo"),
            ...ProductScreen.clickOrderline("Combo Product 3"),
            ...ProductScreen.selectedOrderlineHas("Combo Product 3", "1.0", "13.43"),
            ...ProductScreen.clickOrderline("Combo Product 5"),
            ...ProductScreen.selectedOrderlineHas("Combo Product 5", "1.0", "18.67"),
            ...ProductScreen.clickOrderline("Combo Product 8"),
            ...ProductScreen.selectedOrderlineHas("Combo Product 8", "1.0", "30.00"),

            // check that you can select a customer which triggers a recomputation of the price
            ...ProductScreen.clickPartnerButton(),
            ...ProductScreen.clickCustomer("Partner Test 1"),

            // check that you can change the quantity of a combo product
            ...ProductScreen.clickNumpad("2"),
            ...ProductScreen.clickOrderline("Combo Product 3", "2.0"),
            ...ProductScreen.selectedOrderlineHas("Combo Product 3", "2.0", "26.86"),
            ...ProductScreen.clickOrderline("Combo Product 5", "2.0"),
            ...ProductScreen.selectedOrderlineHas("Combo Product 5", "2.0", "37.34"),
            ...ProductScreen.clickOrderline("Combo Product 8", "2.0"),
            ...ProductScreen.selectedOrderlineHas("Combo Product 8", "2.0", "60.00"),

            // check that removing a combo product removes all the combo products
            ...ProductScreen.clickNumpad("⌫"),
            ...ProductScreen.clickNumpad("⌫"),
            ...ProductScreen.orderIsEmpty(),

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
            ProductScreen.selectedOrderlineHas("Desk Combo"),
            ProductScreen.clickOrderline("Desk Organizer"),
            ProductScreen.selectedOrderlineHas("Desk Organizer", "1.0", "4.45"),
            ProductScreen.clickOrderline("Desk Pad"),
            ProductScreen.selectedOrderlineHas("Desk Pad", "1.0", "1.59"),
            ProductScreen.clickOrderline("Whiteboard Pen"),
            ProductScreen.selectedOrderlineHas("Whiteboard Pen", "1.0", "0.96"),
            ProductScreen.totalAmountIs("7.00"),
            ProductScreen.clickPayButton(),
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
            ProductScreen.clickFiscalPosition("test fp"),
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
