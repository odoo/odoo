import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";
import { escapeRegExp } from "@web/core/utils/strings";
import { registry } from "@web/core/registry";

export function clickDownPaymentNumpad(num) {
    return {
        content: `click discount numpad button: ${num}`,
        trigger: `.o_dialog div.numpad button:contains(/^${escapeRegExp(num)}$/)`,
        run: "click",
    };
}

export function addDownPayment(percentage, soNth, downPaymentType) {
    const steps = [
        ProductScreen.clickControlButton("Quotation/Order"),
        {
            content: "Select the first SO",
            trigger: `.o_sale_order .o_data_row:nth-child(${soNth}) .o_data_cell:nth-child(1)`,
            run: "click",
        },
    ];
    if (downPaymentType === "percent") {
        steps.push({
            content: "Select 'Apply a down payment (percentage)'",
            trigger: ".modal-body button:contains('percentage')",
            run: "click",
        });
    } else {
        steps.push({
            content: "Select 'Apply a down payment (fixed amount)'",
            trigger: ".modal-body button:contains('fixed amount')",
            run: "click",
        });
    }
    for (const num of percentage.split("")) {
        steps.push(clickDownPaymentNumpad(num));
    }
    steps.push({
        content: "Select 'Apply'",
        trigger: ".modal-dialog button.btn-primary:contains('Apply')",
        run: "click",
    });
    return steps;
}

export function payAndInvoice(totalAmount) {
    return [
        ProductScreen.clickPayButton(),

        PaymentScreen.totalIs(totalAmount),
        PaymentScreen.clickPaymentMethod("Bank"),
        PaymentScreen.remainingIs("0.0"),

        PaymentScreen.clickInvoiceButton(),
        PaymentScreen.clickValidate(),

        ReceiptScreen.receiptAmountTotalIs(totalAmount),
        ReceiptScreen.clickNextOrder(),
    ];
}

registry
    .category("web_tour.tours")
    .add("test_taxes_l10n_in_pos_downpayment_round_per_line_price_excluded", {
        steps: () =>
            [
                Chrome.startPoS(),
                Dialog.confirm("Open Register"),

                ...addDownPayment("2", 1, "percent"),
                ProductScreen.checkTotalAmount("0.73"),
                ProductScreen.checkTaxAmount("0.10"),
                ...payAndInvoice("0.73"),
                ...addDownPayment("0.73", 2, "fixed"),
                ProductScreen.checkTotalAmount("0.73"),
                ProductScreen.checkTaxAmount("0.10"),
                ...payAndInvoice("0.73"),
                ...addDownPayment("7", 3, "percent"),
                ProductScreen.checkTotalAmount("2.56"),
                ProductScreen.checkTaxAmount("0.33"),
                ...payAndInvoice("2.56"),
                ...addDownPayment("2.56", 4, "fixed"),
                ProductScreen.checkTotalAmount("2.56"),
                ProductScreen.checkTaxAmount("0.33"),
                ...payAndInvoice("2.56"),
                ...addDownPayment("18", 5, "percent"),
                ProductScreen.checkTotalAmount("6.60"),
                ProductScreen.checkTaxAmount("0.87"),
                ...payAndInvoice("6.60"),
                ...addDownPayment("6.60", 6, "fixed"),
                ProductScreen.checkTotalAmount("6.60"),
                ProductScreen.checkTaxAmount("0.87"),
                ...payAndInvoice("6.60"),
            ].flat(),
    });

registry
    .category("web_tour.tours")
    .add("test_taxes_l10n_in_pos_downpayment_round_globally_price_excluded", {
        steps: () =>
            [
                Chrome.startPoS(),
                Dialog.confirm("Open Register"),

                ...addDownPayment("2", 1, "percent"),
                ProductScreen.checkTotalAmount("0.73"),
                ProductScreen.checkTaxAmount("0.1"),
                ...payAndInvoice("0.73"),
                ...addDownPayment("0.73", 2, "fixed"),
                ProductScreen.checkTotalAmount("0.73"),
                ProductScreen.checkTaxAmount("0.1"),
                ...payAndInvoice("0.73"),
                ...addDownPayment("7", 3, "percent"),
                ProductScreen.checkTotalAmount("2.57"),
                ProductScreen.checkTaxAmount("0.33"),
                ...payAndInvoice("2.57"),
                ...addDownPayment("2.57", 4, "fixed"),
                ProductScreen.checkTotalAmount("2.57"),
                ProductScreen.checkTaxAmount("0.33"),
                ...payAndInvoice("2.57"),
                ...addDownPayment("18", 5, "percent"),
                ProductScreen.checkTotalAmount("6.60"),
                ProductScreen.checkTaxAmount("0.87"),
                ...payAndInvoice("6.60"),
                ...addDownPayment("6.60", 6, "fixed"),
                ProductScreen.checkTotalAmount("6.60"),
                ProductScreen.checkTaxAmount("0.87"),
                ...payAndInvoice("6.60"),
            ].flat(),
    });

registry
    .category("web_tour.tours")
    .add("test_taxes_l10n_in_pos_downpayment_round_per_line_price_included", {
        steps: () =>
            [
                Chrome.startPoS(),
                Dialog.confirm("Open Register"),

                ...addDownPayment("2", 1, "percent"),
                ProductScreen.checkTotalAmount("0.73"),
                ProductScreen.checkTaxAmount("0.10"),
                ...payAndInvoice("0.73"),
                ...addDownPayment("0.73", 2, "fixed"),
                ProductScreen.checkTotalAmount("0.73"),
                ProductScreen.checkTaxAmount("0.10"),
                ...payAndInvoice("0.73"),
                ...addDownPayment("7", 3, "percent"),
                ProductScreen.checkTotalAmount("2.56"),
                ProductScreen.checkTaxAmount("0.33"),
                ...payAndInvoice("2.56"),
                ...addDownPayment("2.56", 4, "fixed"),
                ProductScreen.checkTotalAmount("2.56"),
                ProductScreen.checkTaxAmount("0.33"),
                ...payAndInvoice("2.56"),
                ...addDownPayment("18", 5, "percent"),
                ProductScreen.checkTotalAmount("6.60"),
                ProductScreen.checkTaxAmount("0.87"),
                ...payAndInvoice("6.60"),
                ...addDownPayment("6.60", 6, "fixed"),
                ProductScreen.checkTotalAmount("6.60"),
                ProductScreen.checkTaxAmount("0.87"),
                ...payAndInvoice("6.60"),
            ].flat(),
    });

registry
    .category("web_tour.tours")
    .add("test_taxes_l10n_in_pos_downpayment_round_globally_price_included", {
        steps: () =>
            [
                Chrome.startPoS(),
                Dialog.confirm("Open Register"),

                ...addDownPayment("2", 1, "percent"),
                ProductScreen.checkTotalAmount("0.73"),
                ProductScreen.checkTaxAmount("0.10"),
                ...payAndInvoice("0.73"),
                ...addDownPayment("0.73", 2, "fixed"),
                ProductScreen.checkTotalAmount("0.73"),
                ProductScreen.checkTaxAmount("0.10"),
                ...payAndInvoice("0.73"),
                ...addDownPayment("7", 3, "percent"),
                ProductScreen.checkTotalAmount("2.57"),
                ProductScreen.checkTaxAmount("0.33"),
                ...payAndInvoice("2.57"),
                ...addDownPayment("2.57", 4, "fixed"),
                ProductScreen.checkTotalAmount("2.57"),
                ProductScreen.checkTaxAmount("0.34"),
                ...payAndInvoice("2.57"),
                ...addDownPayment("18", 5, "percent"),
                ProductScreen.checkTotalAmount("6.60"),
                ProductScreen.checkTaxAmount("0.87"),
                ...payAndInvoice("6.60"),
                ...addDownPayment("6.60", 6, "fixed"),
                ProductScreen.checkTotalAmount("6.60"),
                ProductScreen.checkTaxAmount("0.87"),
                ...payAndInvoice("6.60"),
            ].flat(),
    });

registry
    .category("web_tour.tours")
    .add("test_taxes_l10n_br_pos_downpayment_round_per_line_price_excluded", {
        steps: () =>
            [
                Chrome.startPoS(),
                Dialog.confirm("Open Register"),

                ...addDownPayment("2", 1, "percent"),
                ProductScreen.checkTotalAmount("1.92"),
                ProductScreen.checkTaxAmount("0.63"),
                ...payAndInvoice("1.92"),
            ].flat(),
    });

registry
    .category("web_tour.tours")
    .add("test_taxes_l10n_br_pos_downpayment_round_globally_price_excluded", {
        steps: () =>
            [
                Chrome.startPoS(),
                Dialog.confirm("Open Register"),

                ...addDownPayment("2", 1, "percent"),
                ProductScreen.checkTotalAmount("1.92"),
                ProductScreen.checkTaxAmount("0.63"),
                ...payAndInvoice("1.92"),
            ].flat(),
    });

registry
    .category("web_tour.tours")
    .add("test_taxes_l10n_br_pos_downpayment_round_per_line_price_included", {
        steps: () =>
            [
                Chrome.startPoS(),
                Dialog.confirm("Open Register"),

                ...addDownPayment("2", 1, "percent"),
                ProductScreen.checkTotalAmount("1.92"),
                ProductScreen.checkTaxAmount("0.63"),
                ...payAndInvoice("1.92"),
            ].flat(),
    });

registry
    .category("web_tour.tours")
    .add("test_taxes_l10n_br_pos_downpayment_round_globally_price_included", {
        steps: () =>
            [
                Chrome.startPoS(),
                Dialog.confirm("Open Register"),

                ...addDownPayment("2", 1, "percent"),
                ProductScreen.checkTotalAmount("1.92"),
                ProductScreen.checkTaxAmount("0.63"),
                ...payAndInvoice("1.92"),
            ].flat(),
    });

registry
    .category("web_tour.tours")
    .add("test_taxes_l10n_be_pos_downpayment_round_per_line_price_excluded", {
        steps: () =>
            [
                Chrome.startPoS(),
                Dialog.confirm("Open Register"),

                ...addDownPayment("2", 1, "percent"),
                ProductScreen.checkTotalAmount("0.86"),
                ProductScreen.checkTaxAmount("0.15"),
                ...payAndInvoice("0.86"),
            ].flat(),
    });

registry
    .category("web_tour.tours")
    .add("test_taxes_l10n_be_pos_downpayment_round_globally_price_excluded", {
        steps: () =>
            [
                Chrome.startPoS(),
                Dialog.confirm("Open Register"),

                ...addDownPayment("2", 1, "percent"),
                ProductScreen.checkTotalAmount("0.86"),
                ProductScreen.checkTaxAmount("0.15"),
                ...payAndInvoice("0.86"),
            ].flat(),
    });

registry
    .category("web_tour.tours")
    .add("test_taxes_l10n_be_pos_downpayment_round_per_line_price_included", {
        steps: () =>
            [
                Chrome.startPoS(),
                Dialog.confirm("Open Register"),

                ...addDownPayment("2", 1, "percent"),
                ProductScreen.checkTotalAmount("0.86"),
                ProductScreen.checkTaxAmount("0.15"),
                ...payAndInvoice("0.86"),
            ].flat(),
    });

registry
    .category("web_tour.tours")
    .add("test_taxes_l10n_be_pos_downpayment_round_globally_price_included", {
        steps: () =>
            [
                Chrome.startPoS(),
                Dialog.confirm("Open Register"),

                ...addDownPayment("2", 1, "percent"),
                ProductScreen.checkTotalAmount("0.86"),
                ProductScreen.checkTaxAmount("0.15"),
                ...payAndInvoice("0.86"),
            ].flat(),
    });
