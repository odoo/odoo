/** @odoo-module */

import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/utils/receipt_screen_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import { waitForLoading } from "@point_of_sale/../tests/tours/utils/common";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_ship_later_kit_and_mto_manufactured_product", {
    steps: () =>
        [
            waitForLoading(),
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickInfoProduct("Finished"),
            Dialog.confirm("Ok"),
            Dialog.isNot(),
            ProductScreen.clickInfoProduct("Basic Kit"),
            Dialog.confirm("Ok"),
            Dialog.isNot(),
            ProductScreen.addOrderline("Finished", "1"),
            ProductScreen.addOrderline("Basic Kit", "1"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AAAA Super Customer"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickShipLaterButton(),
            PaymentScreen.shippingLaterHighlighted(),
            PaymentScreen.clickValidate(),
            ReceiptScreen.receiptIsThere(),
        ].flat(),
});
