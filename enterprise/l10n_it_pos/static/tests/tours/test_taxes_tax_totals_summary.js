import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/utils/receipt_screen_util";
import { registry } from "@web/core/registry";

function addDocument(documentParams) {
    const steps = [];
    for (const values of documentParams) {
        steps.push(...ProductScreen.addOrderline(values.product, values.quantity));
        if (values.discount) {
            steps.push(ProductScreen.addDiscount(values.discount));
        }
    }
    steps.push(
        ...[
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AAAAAA"),
            ProductScreen.clickPayButton(),
        ]
    );
    return steps;
}

function assertTaxTotals(baseAmount, taxAmount, totalAmount) {
    return [
        PaymentScreen.totalIs(totalAmount),
        PaymentScreen.clickPaymentMethod("Bank"),
        PaymentScreen.remainingIs("0.0"),

        PaymentScreen.clickInvoiceButton(),
        PaymentScreen.isInvoiceOptionSelected(),
        PaymentScreen.clickValidate(),

        ReceiptScreen.receiptAmountTotalIs(totalAmount),
        ReceiptScreen.clickNextOrder(),
    ];
}

registry.category("web_tour.tours").add("test_taxes_l10n_it_epson_printer_pos", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ...addDocument([{ product: "product_1_1", quantity: "3" }]),
            ...assertTaxTotals("15.49", "3.41", "18.90"),

            ...addDocument([{ product: "product_2_1", quantity: "3" }]),
            ...assertTaxTotals("6.59", "1.45", "8.04"),

            ...addDocument([
                { product: "product_3_1", quantity: "3" },
                { product: "product_3_2", quantity: "3" },
            ]),
            ...assertTaxTotals("22.08", "4.86", "26.94"),

            ...addDocument([{ product: "product_4_1", quantity: "1", discount: "50" }]),
            ...assertTaxTotals("25.00", "5.50", "30.50"),
        ].flat(),
});
