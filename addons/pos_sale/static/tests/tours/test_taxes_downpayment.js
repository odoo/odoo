import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as FeedbackScreen from "@point_of_sale/../tests/pos/tours/utils/feedback_screen_util";
import { escapeRegExp } from "@web/core/utils/strings";
import { registry } from "@web/core/registry";

function addDownPayment(percentage, soNth, downPaymentType) {
    const downPaymentTypeLabel = downPaymentType === "percent" ? "percentage" : "fixed amount";
    return [
        ProductScreen.clickControlButton("Quotation/Order"),
        {
            content: "Select the first SO",
            trigger: `.o_sale_order .o_data_row:nth-child(${soNth}) .o_data_cell:nth-child(1)`,
            run: "click",
        },
        Dialog.is({ title: "What do you want to do?" }),
        {
            content: `Select 'Apply a down payment (${downPaymentTypeLabel})`,
            trigger: `.modal-body button:contains(${downPaymentTypeLabel})`,
            run: "click",
        },
        ...percentage.split("").map((num) => ({
            content: `click discount numpad button: ${num}`,
            trigger: `.o_dialog div.numpad button:contains(/^${escapeRegExp(num)}$/)`,
            run: "click",
        })),
        {
            content:
                "Wait the input value is well filled before apply (just make keydown not wait for interactions)",
            trigger: `.modal .input-symbol .input-value:contains(${percentage})`,
        },
        Dialog.proceed({ title: "Down payment", confirm: "Apply" }),
    ];
}

function payAndInvoice(totalAmount) {
    return [
        ProductScreen.clickPayButton(),

        PaymentScreen.totalIs(totalAmount),
        PaymentScreen.clickPaymentMethod("Bank"),
        PaymentScreen.remainingIs("0.0"),

        PaymentScreen.clickInvoiceButton(),
        PaymentScreen.clickValidate(),

        FeedbackScreen.isShown(),
        FeedbackScreen.checkTicketData({
            total_amount: totalAmount,
        }),
        FeedbackScreen.clickNextOrder(),
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
                ProductScreen.checkTotalAmount("0.81"),
                ProductScreen.checkTaxAmount("0.14"),
                ...payAndInvoice("0.81"),
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
                ProductScreen.checkTotalAmount("0.81"),
                ProductScreen.checkTaxAmount("0.14"),
                ...payAndInvoice("0.81"),
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
                ProductScreen.checkTotalAmount("0.81"),
                ProductScreen.checkTaxAmount("0.14"),
                ...payAndInvoice("0.81"),
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
                ProductScreen.checkTotalAmount("0.81"),
                ProductScreen.checkTaxAmount("0.14"),
                ...payAndInvoice("0.81"),
            ].flat(),
    });
