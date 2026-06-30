import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";
import * as TicketScreen from "@point_of_sale/../tests/pos/tours/utils/ticket_screen_util";
import { escapeRegExp } from "@web/core/utils/strings";
import { registry } from "@web/core/registry";

export function addDocument(documentParams) {
    const steps = [];
    for (const values of documentParams) {
        steps.push(...ProductScreen.addOrderline(values.product, values.quantity));
    }
    steps.push(...[ProductScreen.clickPartnerButton(), ProductScreen.clickCustomer("AAAAAA")]);
    return steps;
}

export function clickDiscountNumpad(num) {
    return {
        content: `click discount numpad button: ${num}`,
        trigger: `.o_dialog div.numpad button:contains(/^${escapeRegExp(num)}$/)`,
        run: "click",
    };
}

export function addDiscount(percentage) {
    const steps = [ProductScreen.clickControlButton("Discount")];
    for (const num of percentage.split("")) {
        steps.push(clickDiscountNumpad(num));
    }
    steps.push({
        trigger: `.popup-input:contains(/^${escapeRegExp(percentage)}$/)`,
        run: "click",
    });
    steps.push(Dialog.confirm());
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
    .add("test_taxes_l10n_in_pos_global_discount_round_per_line_price_excluded", {
        steps: () =>
            [
                Chrome.startPoS(),
                Dialog.confirm("Open Register"),

                ...addDocument([
                    { product: "product_1_1", quantity: "1" },
                    { product: "product_1_2", quantity: "1" },
                ]),
                ...addDiscount("2"),
                ProductScreen.checkTotalAmount("35.91"),
                ProductScreen.checkTaxAmount("4.76"),
                ...payAndInvoice("35.91"),
                ...addDocument([
                    { product: "product_1_1", quantity: "1" },
                    { product: "product_1_2", quantity: "1" },
                ]),
                ...addDiscount("7"),
                ProductScreen.checkTotalAmount("34.08"),
                ProductScreen.checkTaxAmount("4.53"),
                ...payAndInvoice("34.08"),
                ...addDocument([
                    { product: "product_1_1", quantity: "1" },
                    { product: "product_1_2", quantity: "1" },
                ]),
                ...addDiscount("18"),
                ProductScreen.checkTotalAmount("30.04"),
                ProductScreen.checkTaxAmount("3.99"),
                ...payAndInvoice("30.04"),
                // On refund, check if the global discount line is correctly prorated in the refund order
                ...ProductScreen.clickRefund(),
                TicketScreen.filterIs("Paid"),
                TicketScreen.selectOrder("001"),
                ProductScreen.clickNumpad("1"),
                TicketScreen.confirmRefund(),
                PaymentScreen.totalIs("-17.95"), // -18.32 (product_1_1) + 0.37 (discount)
            ].flat(),
    });

registry
    .category("web_tour.tours")
    .add("test_taxes_l10n_in_pos_global_discount_round_globally_price_excluded", {
        steps: () =>
            [
                Chrome.startPoS(),
                Dialog.confirm("Open Register"),

                ...addDocument([
                    { product: "product_2_1", quantity: "1" },
                    { product: "product_2_2", quantity: "1" },
                ]),
                ...addDiscount("2"),
                ProductScreen.checkTotalAmount("35.94"),
                ProductScreen.checkTaxAmount("4.79"),
                ...payAndInvoice("35.94"),
                ...addDocument([
                    { product: "product_2_1", quantity: "1" },
                    { product: "product_2_2", quantity: "1" },
                ]),
                ...addDiscount("7"),
                ProductScreen.checkTotalAmount("34.10"),
                ProductScreen.checkTaxAmount("4.56"),
                ...payAndInvoice("34.10"),
                ...addDocument([
                    { product: "product_2_1", quantity: "1" },
                    { product: "product_2_2", quantity: "1" },
                ]),
                ...addDiscount("18"),
                ProductScreen.checkTotalAmount("30.07"),
                ProductScreen.checkTaxAmount("4.02"),
                ...payAndInvoice("30.07"),
            ].flat(),
    });

registry
    .category("web_tour.tours")
    .add("test_taxes_l10n_in_pos_global_discount_round_per_line_price_included", {
        steps: () =>
            [
                Chrome.startPoS(),
                Dialog.confirm("Open Register"),

                ...addDocument([
                    { product: "product_3_1", quantity: "1" },
                    { product: "product_3_2", quantity: "1" },
                ]),
                ...addDiscount("2"),
                ProductScreen.checkTotalAmount("35.91"),
                ProductScreen.checkTaxAmount("4.76"),
                ...payAndInvoice("35.91"),
                ...addDocument([
                    { product: "product_3_1", quantity: "1" },
                    { product: "product_3_2", quantity: "1" },
                ]),
                ...addDiscount("7"),
                ProductScreen.checkTotalAmount("34.08"),
                ProductScreen.checkTaxAmount("4.53"),
                ...payAndInvoice("34.08"),
                ...addDocument([
                    { product: "product_3_1", quantity: "1" },
                    { product: "product_3_2", quantity: "1" },
                ]),
                ...addDiscount("18"),
                ProductScreen.checkTotalAmount("30.04"),
                ProductScreen.checkTaxAmount("3.99"),
                ...payAndInvoice("30.04"),
            ].flat(),
    });

registry
    .category("web_tour.tours")
    .add("test_taxes_l10n_in_pos_global_discount_round_globally_price_included", {
        steps: () =>
            [
                Chrome.startPoS(),
                Dialog.confirm("Open Register"),

                ...addDocument([
                    { product: "product_4_1", quantity: "1" },
                    { product: "product_4_2", quantity: "1" },
                ]),
                ...addDiscount("2"),
                ProductScreen.checkTotalAmount("35.93"),
                ProductScreen.checkTaxAmount("4.79"),
                ...payAndInvoice("35.93"),
                ...addDocument([
                    { product: "product_4_1", quantity: "1" },
                    { product: "product_4_2", quantity: "1" },
                ]),
                ...addDiscount("7"),
                ProductScreen.checkTotalAmount("34.09"),
                ProductScreen.checkTaxAmount("4.56"),
                ...payAndInvoice("34.09"),
                ...addDocument([
                    { product: "product_4_1", quantity: "1" },
                    { product: "product_4_2", quantity: "1" },
                ]),
                ...addDiscount("18"),
                ProductScreen.checkTotalAmount("30.06"),
                ProductScreen.checkTaxAmount("4.02"),
                ...payAndInvoice("30.06"),
            ].flat(),
    });

registry
    .category("web_tour.tours")
    .add("test_taxes_l10n_br_pos_global_discount_round_per_line_price_excluded", {
        steps: () =>
            [
                Chrome.startPoS(),
                Dialog.confirm("Open Register"),

                ...addDocument([
                    { product: "product_1_1", quantity: "1" },
                    { product: "product_1_2", quantity: "1" },
                ]),
                ...addDiscount("2"),
                ProductScreen.checkTotalAmount("94.08"),
                ProductScreen.checkTaxAmount("30.7"),
                ...payAndInvoice("94.08"),
            ].flat(),
    });

registry
    .category("web_tour.tours")
    .add("test_taxes_l10n_br_pos_global_discount_round_globally_price_excluded", {
        steps: () =>
            [
                Chrome.startPoS(),
                Dialog.confirm("Open Register"),

                ...addDocument([
                    { product: "product_2_1", quantity: "1" },
                    { product: "product_2_2", quantity: "1" },
                ]),
                ...addDiscount("2"),
                ProductScreen.checkTotalAmount("94.08"),
                ProductScreen.checkTaxAmount("30.71"),
                ...payAndInvoice("94.08"),
            ].flat(),
    });

registry
    .category("web_tour.tours")
    .add("test_taxes_l10n_br_pos_global_discount_round_per_line_price_included", {
        steps: () =>
            [
                Chrome.startPoS(),
                Dialog.confirm("Open Register"),

                ...addDocument([
                    { product: "product_3_1", quantity: "1" },
                    { product: "product_3_2", quantity: "1" },
                ]),
                ...addDiscount("2"),
                ProductScreen.checkTotalAmount("94.08"),
                ProductScreen.checkTaxAmount("30.7"),
                ...payAndInvoice("94.08"),
            ].flat(),
    });

registry
    .category("web_tour.tours")
    .add("test_taxes_l10n_br_pos_global_discount_round_globally_price_included", {
        steps: () =>
            [
                Chrome.startPoS(),
                Dialog.confirm("Open Register"),

                ...addDocument([
                    { product: "product_4_1", quantity: "1" },
                    { product: "product_4_2", quantity: "1" },
                ]),
                ...addDiscount("2"),
                ProductScreen.checkTotalAmount("94.08"),
                ProductScreen.checkTaxAmount("30.71"),
                ...payAndInvoice("94.08"),
            ].flat(),
    });

registry
    .category("web_tour.tours")
    .add("test_taxes_l10n_be_pos_global_discount_round_per_line_price_excluded", {
        steps: () =>
            [
                Chrome.startPoS(),
                Dialog.confirm("Open Register"),

                ...addDocument([
                    { product: "product_1_1", quantity: "1" },
                    { product: "product_1_2", quantity: "1" },
                ]),
                ...addDiscount("2"),
                ProductScreen.checkTotalAmount("42.25"),
                ProductScreen.checkTaxAmount("9.34"),
                ...payAndInvoice("42.25"),
            ].flat(),
    });

registry
    .category("web_tour.tours")
    .add("test_taxes_l10n_be_pos_global_discount_round_globally_price_excluded", {
        steps: () =>
            [
                Chrome.startPoS(),
                Dialog.confirm("Open Register"),

                ...addDocument([
                    { product: "product_2_1", quantity: "1" },
                    { product: "product_2_2", quantity: "1" },
                ]),
                ...addDiscount("2"),
                ProductScreen.checkTotalAmount("42.24"),
                ProductScreen.checkTaxAmount("9.33"),
                ...payAndInvoice("42.24"),
            ].flat(),
    });

registry
    .category("web_tour.tours")
    .add("test_taxes_l10n_be_pos_global_discount_round_per_line_price_included", {
        steps: () =>
            [
                Chrome.startPoS(),
                Dialog.confirm("Open Register"),

                ...addDocument([
                    { product: "product_3_1", quantity: "1" },
                    { product: "product_3_2", quantity: "1" },
                ]),
                ...addDiscount("2"),
                ProductScreen.checkTotalAmount("42.25"),
                ProductScreen.checkTaxAmount("9.34"),
                ...payAndInvoice("42.25"),
            ].flat(),
    });

registry
    .category("web_tour.tours")
    .add("test_taxes_l10n_be_pos_global_discount_round_globally_price_included", {
        steps: () =>
            [
                Chrome.startPoS(),
                Dialog.confirm("Open Register"),

                ...addDocument([
                    { product: "product_4_1", quantity: "1" },
                    { product: "product_4_2", quantity: "1" },
                ]),
                ...addDiscount("2"),
                ProductScreen.checkTotalAmount("42.25"),
                ProductScreen.checkTaxAmount("9.33"),
                ...payAndInvoice("42.25"),
            ].flat(),
    });
