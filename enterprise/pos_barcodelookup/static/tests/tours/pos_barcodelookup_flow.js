import { registry } from "@web/core/registry";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";

registry.category("web_tour.tours").add("PosBarcodelookupFlow", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            Chrome.clickMenuOption("Create Product"),
            {
                content: "Enter barcode to fetch product data using barcodelookup.",
                trigger: 'div[name="barcode"] input',
                run: "edit 710535977349",
            },
            Dialog.confirm("Save"),
            // new product will be available in pos by default so let's order.
            ProductScreen.addOrderline("Odoo Scale up", "1"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.remainingIs("0.0"),
            PaymentScreen.clickValidate(),
        ].flat(),
});
