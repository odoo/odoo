/** @odoo-module */

import { ProductScreen } from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import { PaymentScreen } from "@point_of_sale/../tests/tours/helpers/PaymentScreenTourMethods";
import { ReceiptScreen } from "@point_of_sale/../tests/tours/helpers/ReceiptScreenTourMethods";
import { ErrorPopup } from "@point_of_sale/../tests/tours/helpers/ErrorPopupTourMethods";
import { combo } from "@point_of_sale/../tests/tours/helpers/ComboPopupMethods";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("PosComboPriceTaxIncludedTour", {
    test: true,
    url: "/pos/ui",
    steps: () => [
        ...ProductScreen.do.confirmOpeningPopup(),
        ...ProductScreen.do.clickDisplayedProduct("Office Combo"),
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
        {
            content: "check that the total amount is properly displayed",
            trigger: `.combo-configurator-popup .total-amount:contains("59.60")`,
            isCheck: true,
        },
        combo.confirm(),
        ...ProductScreen.check.selectedOrderlineHas("Office Combo"),
        ...ProductScreen.do.clickOrderline("Combo Product 3"),
        ...ProductScreen.check.selectedOrderlineHas(
            "Combo Product 3",
            "1.0",
            "12.92",
            "Office Combo"
        ),
        ...ProductScreen.do.clickOrderline("Combo Product 5"),
        ...ProductScreen.check.selectedOrderlineHas(
            "Combo Product 5",
            "1.0",
            "17.87",
            "Office Combo"
        ),
        ...ProductScreen.do.clickOrderline("Combo Product 8"),
        ...ProductScreen.check.selectedOrderlineHas(
            "Combo Product 8",
            "1.0",
            "28.81",
            "Office Combo"
        ),

        // check that you cannot change the quantity of a combo product
        ...ProductScreen.do.pressNumpad("2"),
        ...ErrorPopup.do.clickConfirm(),

        // check that removing a combo product removes all the combo products
        ...ProductScreen.do.pressNumpad("⌫"),
        ...ProductScreen.check.orderIsEmpty(),

        ...ProductScreen.do.clickDisplayedProduct("Office Combo"),
        combo.select("Combo Product 3"),
        combo.select("Combo Product 5"),
        combo.select("Combo Product 8"),
        combo.confirm(),
        ...ProductScreen.check.totalAmountIs("59.60"),
        ...ProductScreen.do.clickPayButton(),
        ...PaymentScreen.do.clickPaymentMethod("Bank"),
        ...PaymentScreen.do.clickValidate(),
        ...ReceiptScreen.check.isShown(),
        ...ReceiptScreen.do.clickNextOrder(),

        // another order but won't be sent to the backend
        ...ProductScreen.do.clickDisplayedProduct("Office Combo"),
        combo.select("Combo Product 2"),
        combo.select("Combo Product 4"),
        combo.select("Combo Product 6"),
        combo.confirm(),
        ...ProductScreen.check.totalAmountIs("50.00"),
        ...ProductScreen.check.totalTaxIs("8.92"),

        // the split screen is tested in `pos_restaurant`
    ],
});
