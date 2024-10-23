import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_cash_rounding_order_with_invoice", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("random_product", "1"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("partner_a"),
            ProductScreen.clickPayButton(),

            PaymentScreen.clickPaymentMethod("Cash"),

            PaymentScreen.clickInvoiceButton(),
            PaymentScreen.clickValidate(),
        ].flat(),
});
