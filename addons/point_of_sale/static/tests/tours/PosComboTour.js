/** @odoo-module */

import * as ProductScreen from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import * as PaymentScreen from "@point_of_sale/../tests/tours/helpers/PaymentScreenTourMethods";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/helpers/ReceiptScreenTourMethods";
import * as ErrorPopup from "@point_of_sale/../tests/tours/helpers/ErrorPopupTourMethods";
import * as combo from "@point_of_sale/../tests/tours/helpers/ComboPopupMethods";
import * as Order from "@point_of_sale/../tests/tours/helpers/generic_components/OrderWidgetMethods";
import { inLeftSide } from "@point_of_sale/../tests/tours/helpers/utils";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("PosComboPriceTaxIncludedTour", {
    test: true,
    url: "/pos/ui",
    steps: () => [
        ...ProductScreen.confirmOpeningPopup(),
        ...ProductScreen.clickDisplayedProduct("Office Combo"),
        combo.isPopupShown(),
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
        combo.confirm(),
        ...ProductScreen.selectedOrderlineHas("Office Combo"),
        ...ProductScreen.clickOrderline("Combo Product 3"),
        ...ProductScreen.selectedOrderlineHas("Combo Product 3", "1.0", "13.43"),
        ...ProductScreen.clickOrderline("Combo Product 5"),
        ...ProductScreen.selectedOrderlineHas("Combo Product 5", "1.0", "18.67"),
        ...ProductScreen.clickOrderline("Combo Product 8"),
        ...ProductScreen.selectedOrderlineHas("Combo Product 8", "1.0", "30.00"),

        // check that you cannot change the quantity of a combo product
        ...ProductScreen.pressNumpad("2"),
        ...ErrorPopup.clickConfirm(),

        // check that removing a combo product removes all the combo products
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
