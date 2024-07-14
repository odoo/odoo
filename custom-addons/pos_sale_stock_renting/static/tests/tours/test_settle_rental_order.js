/** @odoo-module **/

import * as ProductScreenPos from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import * as ProductScreenSale from "@pos_sale/../tests/helpers/ProductScreenTourMethods";
const ProductScreen = { ...ProductScreenPos, ...ProductScreenSale };
import * as PaymentScreen from "@point_of_sale/../tests/tours/helpers/PaymentScreenTourMethods";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/helpers/ReceiptScreenTourMethods";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("OrderLotsRentalTour", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            ProductScreen.clickQuotationButton(),
            ProductScreen.selectFirstOrder(),
            enterSerialNumber("123456789"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
        ].flat(),
});

export function enterSerialNumber(serialNumber) {
    return [
        {
            content: `click serial number icon'`,
            trigger: ".line-lot-icon",
            run: "click",
        },
        {
            content: `insert serial number '${serialNumber}'`,
            trigger: ".popup-input.list-line-input",
            run: "text " + serialNumber,
        },
        {
            content: `click validate button'`,
            trigger: ".button.confirm",
            run: "click",
        },
    ];
}
