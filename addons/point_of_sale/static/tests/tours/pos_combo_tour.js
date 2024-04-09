/** @odoo-module */

import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/utils/receipt_screen_util";
import * as combo from "@point_of_sale/../tests/tours/utils/combo_popup_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as Order from "@point_of_sale/../tests/tours/utils/generic_components/order_widget_util";
import { inLeftSide } from "@point_of_sale/../tests/tours/utils/common";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("PosComboPriceTaxIncludedTour", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),
            ...ProductScreen.clickDisplayedProduct("Office Combo"),
            combo.select("Combo Product 3"),
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

            // check that you cannot change the quantity of a combo product
            ...ProductScreen.clickNumpad("2"),
            Dialog.confirm(),

            // check that removing a combo product removes all the combo products
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
