/* global posmodel */

import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/utils/receipt_screen_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";

import { registry } from "@web/core/registry";

class FiscalDataModuleDummy {
    async action() {
        return { result: true };
    }
    addListener(callback) {
        callback({
            status: "ok",
            value: { error: null },
            signature_controle: "abc",
            unit_id: "123",
        });
    }
}

registry.category("web_tour.tours").add("test_l10n_se_pos_01", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            {
                content: "mock the connected fiscal data moudle",
                trigger: ".pos .pos-content",
                run: function () {
                    posmodel.hardwareProxy.deviceControllers.fiscal_data_module =
                        new FiscalDataModuleDummy();
                },
            },
            ProductScreen.clickDisplayedProduct("Magnetic Board"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            ReceiptScreen.receiptIsThere(),
        ].flat(),
});
