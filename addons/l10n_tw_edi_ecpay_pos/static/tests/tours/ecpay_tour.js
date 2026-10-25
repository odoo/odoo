/* Part of Odoo. See LICENSE file for full copyright and licensing details. */

import { registry } from "@web/core/registry";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";

registry
    .category("web_tour.tours")
    .add("l10n_tw_edi_ecpay_pos.ecpay_b2c_check_mobile_barcode_tour", {
        steps: () =>
            [
                Chrome.startPoS(),
                Dialog.confirm("Open Register"),
                ProductScreen.addOrderline("product_a", "1"),
                ProductScreen.clickPayButton(),
                PaymentScreen.clickInvoiceButton(),
                PaymentScreen.clickInvoiceButton(),
                Dialog.confirm("Yes"),
                {
                    content: "Show EcPay info popup",
                    trigger: "#ecpay_info_screen",
                },
                {
                    content: "Select carrier type",
                    trigger: "select[name='l10n_tw_edi_carrier_type']",
                    run: "select 3",
                },
                {
                    content: "Enter carrier number",
                    trigger: "input[name='l10n_tw_edi_carrier_number']",
                    run: "edit /1234567",
                },
                {
                    content: "Click Validate Carrier Number button",
                    trigger: "#validate_carrier_number",
                    run: "click",
                },
                Dialog.confirm(),
                {
                    content: "Click Cash payment method",
                    trigger: "div.paymentmethod:contains('Cash')",
                    run: "click",
                },
                PaymentScreen.clickValidate(),
                ReceiptScreen.isShown(),
                Chrome.endTour(),
            ].flat(),
    });

registry.category("web_tour.tours").add("l10n_tw_edi_ecpay_pos.ecpay_check_love_code_tour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("product_a", "1"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickInvoiceButton(),
            PaymentScreen.clickInvoiceButton(),
            Dialog.confirm("Yes"),
            {
                content: "Show EcPay info popup",
                trigger: "#ecpay_info_screen",
            },
            {
                content: "Enable donate",
                trigger: "input[name='l10n_tw_edi_is_donate']",
                run: "click",
            },
            {
                content: "Enter love code",
                trigger: "input[name='l10n_tw_edi_love_code']",
                run: "edit 123",
            },
            {
                content: "Validate love code",
                trigger: "#validate_love_code",
                run: "click",
            },
            Dialog.confirm(),
            {
                content: "Click Cash payment method",
                trigger: "div.paymentmethod:contains('Cash')",
                run: "click",
            },
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("l10n_tw_edi_ecpay_pos.ecpay_check_print_invoice_tour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("product_a", "1"),
            ProductScreen.clickPayButton(),
            {
                content: "Click Cash payment method",
                trigger: "div.paymentmethod:contains('Cash')",
                run: "click",
            },
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("l10n_tw_edi_ecpay_pos.ecpay_toggle_invoice_tour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("product_a", "1"),
            ProductScreen.clickPayButton(),
            {
                content: "Click Cash payment method",
                trigger: "div.paymentmethod:contains('Cash')",
                run: "click",
            },
            PaymentScreen.clickInvoiceButton(),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            Chrome.endTour(),
        ].flat(),
});
