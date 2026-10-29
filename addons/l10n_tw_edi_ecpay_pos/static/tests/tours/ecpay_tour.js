/* Part of Odoo. See LICENSE file for full copyright and licensing details. */
/* global posmodel */

import { registry } from "@web/core/registry";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as FeedbackScreen from "@point_of_sale/../tests/pos/tours/utils/feedback_screen_util";

registry
    .category("web_tour.tours")
    .add("l10n_tw_edi_ecpay_pos.ecpay_b2c_check_mobile_barcode_tour", {
        steps: () =>
            [
                Chrome.startPoS(),
                Dialog.confirm("Open Register"),
                ProductScreen.addOrderline("product_a", "1"),
                ProductScreen.clickPayButton(),
                PaymentScreen.isInvoiceButtonChecked(),
                PaymentScreen.clickInvoiceButton(false),
                PaymentScreen.isInvoiceButtonUnchecked(),
                PaymentScreen.clickInvoiceButton(false),
                Dialog.confirm(),
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
                {
                    content: "Carrier number validated",
                    trigger: "#reenter_carrier_number",
                },
                Dialog.confirm(),
                PaymentScreen.clickPaymentMethod("Cash"),
                PaymentScreen.clickValidate(),
                FeedbackScreen.isShown(),
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
            PaymentScreen.isInvoiceButtonChecked(),
            PaymentScreen.clickInvoiceButton(false),
            PaymentScreen.isInvoiceButtonUnchecked(),
            PaymentScreen.clickInvoiceButton(false),
            Dialog.confirm(),
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
            {
                content: "Love code validated",
                trigger: "#reenter_love_code",
            },
            Dialog.confirm(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
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
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
            {
                content: "Print the POS receipt and both ECPay receipts without a printer",
                trigger: ".feedback-screen .button.validation:not([disabled])",
                async run() {
                    const printer = posmodel.ticketPrinter;
                    const order = posmodel.getOrder();
                    const printed = [];
                    const originalPrint = printer._print;
                    printer._print = (printWindow) => {
                        printed.push(printWindow.document.body.textContent);
                    };
                    try {
                        await printer.printOrderReceipt({ order });
                        if (
                            printed.length !== 3 ||
                            !printed[1].includes("電子發票證明聯") ||
                            !printed[2].includes("交易明細") ||
                            !printed[1].includes("AB11100099") ||
                            !printed[2].includes("AB11100099")
                        ) {
                            throw new Error(
                                `Expected the POS receipt and both ECPay receipts; got ${printed.length} browser prints`
                            );
                        }
                        printed.length = 0;
                        await printer.printOrderReceipt({ order, webFallback: false });
                        if (printed.length) {
                            throw new Error("Browser printing must respect webFallback: false");
                        }
                        await printer.printOrderReceipt({ order, printBillActionTriggered: true });
                        if (printed.length !== 1) {
                            throw new Error(
                                `Expected only the bill on a Bill print; got ${printed.length} browser prints`
                            );
                        }
                    } finally {
                        printer._print = originalPrint;
                    }
                },
            },
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
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickInvoiceButton(),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
            Chrome.endTour(),
        ].flat(),
});
