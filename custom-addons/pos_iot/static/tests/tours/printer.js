/** @odoo-module */

import * as ProductScreen from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import * as PaymentScreen from "@point_of_sale/../tests/tours/helpers/PaymentScreenTourMethods";
import * as PartnerListScreen from "@point_of_sale/../tests/tours/helpers/PartnerListScreenTourMethods";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("PrinterInvoice", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.clickHomeCategory(),
            ProductScreen.addOrderline("Desk Pad", "1", "3"),
            ProductScreen.clickPartnerButton(),
            PartnerListScreen.clickPartner("Deco Addict"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickInvoiceButton(),
            PaymentScreen.clickValidate(),
            {
                trigger: ".modal-title:contains('Select printers')",
            },
        ].flat(),
});
