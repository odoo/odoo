import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";
import { registry } from "@web/core/registry";

export function addDocument(documentParams) {
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

export function assertTaxTotals(baseAmount, taxAmount, totalAmount) {
    return [
        PaymentScreen.totalIs(totalAmount),
        PaymentScreen.clickPaymentMethod("Bank"),
        PaymentScreen.remainingIs("0.0"),

        PaymentScreen.clickInvoiceButton(),
        PaymentScreen.clickValidate(),

        ReceiptScreen.receiptAmountTotalIs(totalAmount),
        ReceiptScreen.clickNextOrder(),
    ];
}

registry.category("web_tour.tours").add("test_point_of_sale_custom_tax_with_extra_product_field", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ...addDocument([{ product: "product_1_1", quantity: "10" }]),
            ...assertTaxTotals("2000.0", "42.0", "2,042.0"),
        ].flat(),
});
