import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";
import * as TicketScreen from "@point_of_sale/../tests/pos/tours/utils/ticket_screen_util";
import { registry } from "@web/core/registry";

registry
    .category("web_tour.tours")
    .add("test_cash_rounding_halfup_add_invoice_line_not_only_round_cash_method", {
        steps: () =>
            [
                Chrome.startPoS(),
                Dialog.confirm("Open Register"),

                // Order.
                ProductScreen.addOrderline("random_product", "1"),
                ProductScreen.checkTaxAmount("2.05"),
                ProductScreen.checkRoundingAmount("-0.02"),
                ProductScreen.checkTotalAmount("15.70"),
                ProductScreen.clickPartnerButton(),
                ProductScreen.clickCustomer("AAAAAA"),
                ProductScreen.clickPayButton(),

                PaymentScreen.totalIs("15.70"),
                PaymentScreen.clickPaymentMethod("Cash"),
                PaymentScreen.remainingIs("0.0"),
                PaymentScreen.clickInvoiceButton(),
                PaymentScreen.clickValidate(),

                ReceiptScreen.receiptAmountTotalIs("15.72"),
                ReceiptScreen.receiptRoundingAmountIs("-0.02"),
                ReceiptScreen.receiptToPayAmountIs("15.70"),
                ReceiptScreen.receiptChangeAmountIsNotThere(),
                ReceiptScreen.clickNextOrder(),

                // Refund.
                Chrome.clickOrders(),
                TicketScreen.selectFilter("Active"),
                TicketScreen.selectFilter("Paid"),

                TicketScreen.selectOrder("0001"),
                TicketScreen.confirmRefund(),

                ProductScreen.checkTaxAmount("-2.05"),
                ProductScreen.checkRoundingAmount("0.02"),
                ProductScreen.checkTotalAmount("-15.70"),
                ProductScreen.clickPayButton(),

                PaymentScreen.totalIs("15.70"),
                PaymentScreen.clickPaymentMethod("Cash"),
                PaymentScreen.remainingIs("0.0"),
                PaymentScreen.clickValidate(),

                ReceiptScreen.receiptAmountTotalIs("-15.72"),
                ReceiptScreen.receiptRoundingAmountIs("0.02"),
                ReceiptScreen.receiptToPayAmountIs("-15.70"),
                ReceiptScreen.receiptChangeAmountIsNotThere(),
                ReceiptScreen.clickNextOrder(),
            ].flat(),
    });

registry
    .category("web_tour.tours")
    .add(
        "test_cash_rounding_halfup_add_invoice_line_not_only_round_cash_method_pay_by_bank_and_cash",
        {
            steps: () =>
                [
                    Chrome.startPoS(),
                    Dialog.confirm("Open Register"),

                    // Order.
                    ProductScreen.addOrderline("random_product", "1"),
                    ProductScreen.checkTaxAmount("2.05"),
                    ProductScreen.checkRoundingAmount("-0.02"),
                    ProductScreen.checkTotalAmount("15.70"),
                    ProductScreen.clickPartnerButton(),
                    ProductScreen.clickCustomer("AAAAAA"),
                    ProductScreen.clickPayButton(),

                    PaymentScreen.totalIs("15.70"),
                    PaymentScreen.clickPaymentMethod("Bank"),
                    PaymentScreen.clickNumpad("0 . 6 8"),
                    PaymentScreen.fillPaymentLineAmountMobile("Bank", "0.68"),
                    PaymentScreen.remainingIs("15.02"),
                    PaymentScreen.clickPaymentMethod("Cash"),
                    PaymentScreen.remainingIs("0.0"),
                    PaymentScreen.clickInvoiceButton(),
                    PaymentScreen.clickValidate(),

                    ReceiptScreen.receiptAmountTotalIs("15.72"),
                    ReceiptScreen.receiptRoundingAmountIs("0.01"),
                    ReceiptScreen.receiptToPayAmountIs("15.73"),
                    ReceiptScreen.receiptChangeAmountIsNotThere(),
                    ReceiptScreen.clickNextOrder(),

                    // Refund.
                    Chrome.clickOrders(),
                    TicketScreen.selectFilter("Active"),
                    TicketScreen.selectFilter("Paid"),
                    TicketScreen.selectOrder("0001"),
                    TicketScreen.confirmRefund(),

                    ProductScreen.checkTaxAmount("-2.05"),
                    ProductScreen.checkRoundingAmount("0.02"),
                    ProductScreen.checkTotalAmount("-15.70"),
                    ProductScreen.clickPayButton(),

                    PaymentScreen.totalIs("-15.70"),
                    PaymentScreen.clickPaymentMethod("Bank"),
                    PaymentScreen.clickNumpad("0 . 6 8 +/-"),
                    PaymentScreen.fillPaymentLineAmountMobile("Bank", "0.68"),
                    PaymentScreen.remainingIs("-15.02"),
                    PaymentScreen.clickPaymentMethod("Cash"),
                    PaymentScreen.remainingIs("0.0"),
                    PaymentScreen.clickValidate(),

                    ReceiptScreen.receiptAmountTotalIs("-15.72"),
                    ReceiptScreen.receiptRoundingAmountIs("-0.01"),
                    ReceiptScreen.receiptToPayAmountIs("-15.73"),
                    ReceiptScreen.receiptChangeAmountIsNotThere(),
                    ReceiptScreen.clickNextOrder(),
                ].flat(),
        }
    );

registry
    .category("web_tour.tours")
    .add("test_cash_rounding_down_add_invoice_line_not_only_round_cash_method_no_rounding_left", {
        steps: () =>
            [
                Chrome.startPoS(),
                Dialog.confirm("Open Register"),

                // Order.
                ProductScreen.addOrderline("random_product", "1"),
                ProductScreen.checkTaxAmount("2.05"),
                ProductScreen.checkRoundingAmount("-0.02"),
                ProductScreen.checkTotalAmount("15.70"),
                ProductScreen.clickPartnerButton(),
                ProductScreen.clickCustomer("AAAAAA"),
                ProductScreen.clickPayButton(),

                PaymentScreen.totalIs("15.70"),
                PaymentScreen.clickPaymentMethod("Bank"),
                PaymentScreen.clickNumpad("0 . 6 7"),
                PaymentScreen.fillPaymentLineAmountMobile("Bank", "0.67"),
                PaymentScreen.remainingIs("15.03"),
                PaymentScreen.clickPaymentMethod("Cash"),
                PaymentScreen.remainingIs("0.0"),
                PaymentScreen.clickInvoiceButton(),
                PaymentScreen.clickValidate(),

                ReceiptScreen.receiptAmountTotalIs("15.72"),
                ReceiptScreen.receiptRoundingAmountIsNotThere(),
                ReceiptScreen.receiptToPayAmountIsNotThere(),
                ReceiptScreen.receiptChangeAmountIsNotThere(),
                ReceiptScreen.clickNextOrder(),

                // Refund.
                Chrome.clickOrders(),
                TicketScreen.selectFilter("Active"),
                TicketScreen.selectFilter("Paid"),

                TicketScreen.selectOrder("0001"),
                TicketScreen.confirmRefund(),

                ProductScreen.checkTaxAmount("-2.05"),
                ProductScreen.checkRoundingAmount("0.02"),
                ProductScreen.checkTotalAmount("-15.70"),
                ProductScreen.clickPayButton(),

                PaymentScreen.totalIs("-15.70"),
                PaymentScreen.clickPaymentMethod("Bank"),
                PaymentScreen.clickNumpad("0 . 6 7 +/-"),
                PaymentScreen.fillPaymentLineAmountMobile("Bank", "-0.67"),
                PaymentScreen.remainingIs("-15.03"),
                PaymentScreen.clickPaymentMethod("Cash"),
                PaymentScreen.remainingIs("0.0"),
                PaymentScreen.clickValidate(),

                ReceiptScreen.receiptAmountTotalIs("-15.72"),
                ReceiptScreen.receiptRoundingAmountIsNotThere(),
                ReceiptScreen.receiptToPayAmountIsNotThere(),
                ReceiptScreen.receiptChangeAmountIsNotThere(),
                ReceiptScreen.clickNextOrder(),
            ].flat(),
    });

registry
    .category("web_tour.tours")
    .add(
        "test_cash_rounding_down_add_invoice_line_not_only_round_cash_method_with_residual_rounding",
        {
            steps: () =>
                [
                    Chrome.startPoS(),
                    Dialog.confirm("Open Register"),

                    // Order.
                    ProductScreen.addOrderline("random_product", "1"),
                    ProductScreen.checkTaxAmount("2.05"),
                    ProductScreen.checkRoundingAmount("-0.02"),
                    ProductScreen.checkTotalAmount("15.70"),
                    ProductScreen.clickPartnerButton(),
                    ProductScreen.clickCustomer("AAAAAA"),
                    ProductScreen.clickPayButton(),

                    PaymentScreen.totalIs("15.70"),
                    PaymentScreen.clickPaymentMethod("Bank"),
                    PaymentScreen.clickNumpad("0 . 6 8"),
                    PaymentScreen.fillPaymentLineAmountMobile("Bank", "0.68"),
                    PaymentScreen.remainingIs("15.02"),
                    PaymentScreen.clickPaymentMethod("Cash"),
                    PaymentScreen.remainingIs("0.0"),
                    PaymentScreen.clickInvoiceButton(),
                    PaymentScreen.clickValidate(),

                    ReceiptScreen.receiptAmountTotalIs("15.72"),
                    ReceiptScreen.receiptRoundingAmountIs("-0.04"),
                    ReceiptScreen.receiptToPayAmountIs("15.68"),
                    ReceiptScreen.receiptChangeAmountIsNotThere(),
                    ReceiptScreen.clickNextOrder(),

                    // Refund.
                    Chrome.clickOrders(),
                    TicketScreen.selectFilter("Active"),
                    TicketScreen.selectFilter("Paid"),
                    TicketScreen.selectOrder("0001"),
                    TicketScreen.confirmRefund(),

                    ProductScreen.checkTaxAmount("-2.05"),
                    ProductScreen.checkRoundingAmount("0.02"),
                    ProductScreen.checkTotalAmount("-15.70"),
                    ProductScreen.clickPayButton(),

                    PaymentScreen.totalIs("-15.70"),
                    PaymentScreen.clickPaymentMethod("Bank"),
                    PaymentScreen.clickNumpad("0 . 6 8 +/-"),
                    PaymentScreen.fillPaymentLineAmountMobile("Bank", "-0.68"),
                    PaymentScreen.remainingIs("-15.02"),
                    PaymentScreen.clickPaymentMethod("Cash"),
                    PaymentScreen.remainingIs("0.0"),
                    PaymentScreen.clickValidate(),

                    ReceiptScreen.receiptAmountTotalIs("-15.72"),
                    ReceiptScreen.receiptRoundingAmountIs("0.04"),
                    ReceiptScreen.receiptToPayAmountIs("-15.68"),
                    ReceiptScreen.receiptChangeAmountIsNotThere(),
                    ReceiptScreen.clickNextOrder(),
                ].flat(),
        }
    );

registry
    .category("web_tour.tours")
    .add("test_cash_rounding_up_add_invoice_line_not_only_round_cash_method", {
        steps: () =>
            [
                Chrome.startPoS(),
                Dialog.confirm("Open Register"),

                // Order.
                ProductScreen.addOrderline("random_product", "1"),
                ProductScreen.checkTaxAmount("2.05"),
                ProductScreen.checkRoundingAmount("0.03"),
                ProductScreen.checkTotalAmount("15.75"),
                ProductScreen.clickPartnerButton(),
                ProductScreen.clickCustomer("AAAAAA"),
                ProductScreen.clickPayButton(),

                PaymentScreen.totalIs("15.75"),
                PaymentScreen.clickPaymentMethod("Bank"),
                PaymentScreen.clickNumpad("0 . 6 4"),
                PaymentScreen.fillPaymentLineAmountMobile("Bank", "0.64"),
                PaymentScreen.remainingIs("15.11"),
                PaymentScreen.clickPaymentMethod("Cash"),
                PaymentScreen.remainingIs("0.0"),
                PaymentScreen.clickInvoiceButton(),
                PaymentScreen.clickValidate(),

                ReceiptScreen.receiptAmountTotalIs("15.72"),
                ReceiptScreen.receiptRoundingAmountIs("0.02"),
                ReceiptScreen.receiptToPayAmountIs("15.74"),
                ReceiptScreen.receiptChangeAmountIsNotThere(),
                ReceiptScreen.clickNextOrder(),

                // Refund.
                Chrome.clickOrders(),
                TicketScreen.selectFilter("Active"),
                TicketScreen.selectFilter("Paid"),
                TicketScreen.selectOrder("0001"),
                TicketScreen.confirmRefund(),

                ProductScreen.checkTaxAmount("-2.05"),
                ProductScreen.checkRoundingAmount("-0.03"),
                ProductScreen.checkTotalAmount("-15.75"),
                ProductScreen.clickPayButton(),

                PaymentScreen.totalIs("-15.75"),
                PaymentScreen.clickPaymentMethod("Bank"),
                PaymentScreen.clickNumpad("0 . 6 4 +/-"),
                PaymentScreen.fillPaymentLineAmountMobile("Bank", "-0.64"),
                PaymentScreen.remainingIs("-15.11"),
                PaymentScreen.clickPaymentMethod("Cash"),
                PaymentScreen.remainingIs("0.0"),
                PaymentScreen.clickValidate(),

                ReceiptScreen.receiptAmountTotalIs("-15.72"),
                ReceiptScreen.receiptRoundingAmountIs("-0.02"),
                ReceiptScreen.receiptToPayAmountIs("-15.74"),
                ReceiptScreen.receiptChangeAmountIsNotThere(),
                ReceiptScreen.clickNextOrder(),
            ].flat(),
    });

registry
    .category("web_tour.tours")
    .add("test_cash_rounding_halfup_add_invoice_line_only_round_cash_method", {
        steps: () =>
            [
                Chrome.startPoS(),
                Dialog.confirm("Open Register"),

                // Order.
                ProductScreen.addOrderline("random_product", "1"),
                ProductScreen.checkTaxAmount("2.05"),
                ProductScreen.checkRoundingAmountIsNotThere(),
                ProductScreen.checkTotalAmount("15.72"),
                ProductScreen.clickPartnerButton(),
                ProductScreen.clickCustomer("AAAAAA"),
                ProductScreen.clickPayButton(),

                PaymentScreen.totalIs("15.72"),
                PaymentScreen.clickPaymentMethod("Cash"),
                PaymentScreen.remainingIs("0.0"),
                PaymentScreen.clickInvoiceButton(),
                PaymentScreen.clickValidate(),

                ReceiptScreen.receiptAmountTotalIs("15.72"),
                ReceiptScreen.receiptRoundingAmountIs("-0.02"),
                ReceiptScreen.receiptToPayAmountIs("15.70"),
                ReceiptScreen.receiptChangeAmountIsNotThere(),
                ReceiptScreen.clickNextOrder(),

                // Refund.
                Chrome.clickOrders(),
                TicketScreen.selectFilter("Active"),
                TicketScreen.selectFilter("Paid"),
                TicketScreen.selectOrder("0001"),
                TicketScreen.confirmRefund(),

                ProductScreen.checkTaxAmount("-2.05"),
                ProductScreen.checkRoundingAmountIsNotThere(),
                ProductScreen.checkTotalAmount("-15.72"),
                ProductScreen.clickPayButton(),

                PaymentScreen.totalIs("-15.72"),
                PaymentScreen.clickPaymentMethod("Cash"),
                PaymentScreen.remainingIs("0.0"),
                PaymentScreen.clickValidate(),

                ReceiptScreen.receiptAmountTotalIs("-15.72"),
                ReceiptScreen.receiptRoundingAmountIs("0.02"),
                ReceiptScreen.receiptToPayAmountIs("-15.70"),
                ReceiptScreen.receiptChangeAmountIsNotThere(),
                ReceiptScreen.clickNextOrder(),
            ].flat(),
    });

registry
    .category("web_tour.tours")
    .add("test_cash_rounding_halfup_add_invoice_line_only_round_cash_method_pay_by_bank_and_cash", {
        steps: () =>
            [
                Chrome.startPoS(),
                Dialog.confirm("Open Register"),

                // Order.
                ProductScreen.addOrderline("random_product", "1"),
                ProductScreen.checkTaxAmount("2.05"),
                ProductScreen.checkRoundingAmountIsNotThere(),
                ProductScreen.checkTotalAmount("15.72"),
                ProductScreen.clickPartnerButton(),
                ProductScreen.clickCustomer("AAAAAA"),
                ProductScreen.clickPayButton(),

                PaymentScreen.totalIs("15.72"),
                PaymentScreen.clickPaymentMethod("Bank"),
                PaymentScreen.clickNumpad("0 . 6 8"),
                PaymentScreen.fillPaymentLineAmountMobile("Bank", "0.68"),
                PaymentScreen.remainingIs("15.04"),
                PaymentScreen.clickPaymentMethod("Cash"),
                PaymentScreen.remainingIs("0.0"),
                PaymentScreen.clickInvoiceButton(),
                PaymentScreen.clickValidate(),

                ReceiptScreen.receiptAmountTotalIs("15.72"),
                ReceiptScreen.receiptRoundingAmountIs("0.01"),
                ReceiptScreen.receiptToPayAmountIs("15.73"),
                ReceiptScreen.receiptChangeAmountIsNotThere(),
                ReceiptScreen.clickNextOrder(),

                // Refund.
                Chrome.clickOrders(),
                TicketScreen.selectFilter("Active"),
                TicketScreen.selectFilter("Paid"),
                TicketScreen.selectOrder("0001"),
                TicketScreen.confirmRefund(),

                ProductScreen.checkTaxAmount("-2.05"),
                ProductScreen.checkRoundingAmountIsNotThere(),
                ProductScreen.checkTotalAmount("-15.72"),
                ProductScreen.clickPayButton(),

                PaymentScreen.totalIs("-15.72"),
                PaymentScreen.clickPaymentMethod("Bank"),
                PaymentScreen.clickNumpad("0 . 6 8 +/-"),
                PaymentScreen.fillPaymentLineAmountMobile("Bank", "-0.68"),
                PaymentScreen.remainingIs("-15.04"),
                PaymentScreen.clickPaymentMethod("Cash"),
                PaymentScreen.remainingIs("0.0"),
                PaymentScreen.clickValidate(),

                ReceiptScreen.receiptAmountTotalIs("-15.72"),
                ReceiptScreen.receiptRoundingAmountIs("-0.01"),
                ReceiptScreen.receiptToPayAmountIs("-15.73"),
                ReceiptScreen.receiptChangeAmountIsNotThere(),
                ReceiptScreen.clickNextOrder(),
            ].flat(),
    });

registry
    .category("web_tour.tours")
    .add("test_cash_rounding_halfup_biggest_tax_not_only_round_cash_method", {
        steps: () =>
            [
                Chrome.startPoS(),
                Dialog.confirm("Open Register"),

                // Order.
                ProductScreen.addOrderline("random_product", "1"),
                ProductScreen.checkTaxAmount("2.03"),
                ProductScreen.checkRoundingAmountIsNotThere(),
                ProductScreen.checkTotalAmount("15.70"),
                ProductScreen.clickPartnerButton(),
                ProductScreen.clickCustomer("AAAAAA"),
                ProductScreen.clickPayButton(),

                PaymentScreen.totalIs("15.70"),
                PaymentScreen.clickPaymentMethod("Cash"),
                PaymentScreen.remainingIs("0.0"),
                PaymentScreen.clickInvoiceButton(),
                PaymentScreen.clickValidate(),

                ReceiptScreen.receiptAmountTotalIs("15.70"),
                ReceiptScreen.receiptToPayAmountIsNotThere(),
                ReceiptScreen.receiptChangeAmountIsNotThere(),
                ReceiptScreen.clickNextOrder(),

                // Refund.
                Chrome.clickOrders(),
                TicketScreen.selectFilter("Active"),
                TicketScreen.selectFilter("Paid"),
                TicketScreen.selectOrder("0001"),
                TicketScreen.confirmRefund(),

                ProductScreen.checkTaxAmount("-2.03"),
                ProductScreen.checkRoundingAmountIsNotThere(),
                ProductScreen.checkTotalAmount("-15.70"),
                ProductScreen.clickPayButton(),

                PaymentScreen.totalIs("-15.70"),
                PaymentScreen.clickPaymentMethod("Cash"),
                PaymentScreen.remainingIs("0.0"),
                PaymentScreen.clickValidate(),

                ReceiptScreen.receiptAmountTotalIs("-15.70"),
                ReceiptScreen.receiptToPayAmountIsNotThere(),
                ReceiptScreen.receiptChangeAmountIsNotThere(),
                ReceiptScreen.clickNextOrder(),
            ].flat(),
    });

registry
    .category("web_tour.tours")
    .add("test_cash_rounding_halfup_biggest_tax_not_only_round_cash_method_pay_by_bank_and_cash", {
        steps: () =>
            [
                Chrome.startPoS(),
                Dialog.confirm("Open Register"),

                // Order.
                ProductScreen.addOrderline("random_product", "1"),
                ProductScreen.checkTaxAmount("2.03"),
                ProductScreen.checkRoundingAmountIsNotThere(),
                ProductScreen.checkTotalAmount("15.70"),
                ProductScreen.clickPartnerButton(),
                ProductScreen.clickCustomer("AAAAAA"),
                ProductScreen.clickPayButton(),

                PaymentScreen.totalIs("15.70"),
                PaymentScreen.clickPaymentMethod("Bank"),
                PaymentScreen.clickNumpad("0 . 6 7"),
                PaymentScreen.fillPaymentLineAmountMobile("Bank", "0.67"),
                PaymentScreen.remainingIs("15.03"),
                PaymentScreen.clickPaymentMethod("Cash"),
                PaymentScreen.remainingIs("0.0"),
                PaymentScreen.clickInvoiceButton(),
                PaymentScreen.clickValidate(),

                ReceiptScreen.receiptAmountTotalIs("15.70"),
                ReceiptScreen.receiptRoundingAmountIs("0.02"),
                ReceiptScreen.receiptToPayAmountIs("15.72"),
                ReceiptScreen.receiptChangeAmountIsNotThere(),
                ReceiptScreen.clickNextOrder(),

                // Refund.
                Chrome.clickOrders(),
                TicketScreen.selectFilter("Active"),
                TicketScreen.selectFilter("Paid"),
                TicketScreen.selectOrder("0001"),
                TicketScreen.confirmRefund(),

                ProductScreen.checkTaxAmount("-2.03"),
                ProductScreen.checkRoundingAmountIsNotThere(),
                ProductScreen.checkTotalAmount("-15.70"),
                ProductScreen.clickPayButton(),

                PaymentScreen.totalIs("-15.70"),
                PaymentScreen.clickPaymentMethod("Bank"),
                PaymentScreen.clickNumpad("0 . 6 7 +/-"),
                PaymentScreen.fillPaymentLineAmountMobile("Bank", "-0.67"),
                PaymentScreen.remainingIs("-15.03"),
                PaymentScreen.clickPaymentMethod("Cash"),
                PaymentScreen.remainingIs("0.0"),
                PaymentScreen.clickValidate(),

                ReceiptScreen.receiptAmountTotalIs("-15.70"),
                ReceiptScreen.receiptRoundingAmountIs("-0.02"),
                ReceiptScreen.receiptToPayAmountIs("-15.72"),
                ReceiptScreen.receiptChangeAmountIsNotThere(),
                ReceiptScreen.clickNextOrder(),
            ].flat(),
    });

registry
    .category("web_tour.tours")
    .add("test_cash_rounding_halfup_biggest_tax_only_round_cash_method", {
        steps: () =>
            [
                Chrome.startPoS(),
                Dialog.confirm("Open Register"),

                // Order.
                ProductScreen.addOrderline("random_product", "1"),
                ProductScreen.checkTaxAmount("2.05"),
                ProductScreen.checkRoundingAmountIsNotThere(),
                ProductScreen.checkTotalAmount("15.72"),
                ProductScreen.clickPartnerButton(),
                ProductScreen.clickCustomer("AAAAAA"),
                ProductScreen.clickPayButton(),

                PaymentScreen.totalIs("15.72"),
                PaymentScreen.clickPaymentMethod("Cash"),
                PaymentScreen.remainingIs("0.0"),
                PaymentScreen.clickInvoiceButton(),
                PaymentScreen.clickValidate(),

                ReceiptScreen.receiptAmountTotalIs("15.72"),
                ReceiptScreen.receiptRoundingAmountIs("-0.02"),
                ReceiptScreen.receiptToPayAmountIs("15.70"),
                ReceiptScreen.receiptChangeAmountIsNotThere(),
                ReceiptScreen.clickNextOrder(),

                // Refund.
                Chrome.clickOrders(),
                TicketScreen.selectFilter("Active"),
                TicketScreen.selectFilter("Paid"),
                TicketScreen.selectOrder("0001"),
                TicketScreen.confirmRefund(),

                ProductScreen.checkTaxAmount("-2.05"),
                ProductScreen.checkRoundingAmountIsNotThere(),
                ProductScreen.checkTotalAmount("-15.72"),
                ProductScreen.clickPayButton(),

                PaymentScreen.totalIs("-15.72"),
                PaymentScreen.clickPaymentMethod("Cash"),
                PaymentScreen.remainingIs("0.0"),
                PaymentScreen.clickValidate(),

                ReceiptScreen.receiptAmountTotalIs("-15.72"),
                ReceiptScreen.receiptRoundingAmountIs("0.02"),
                ReceiptScreen.receiptToPayAmountIs("-15.70"),
                ReceiptScreen.receiptChangeAmountIsNotThere(),
                ReceiptScreen.clickNextOrder(),
            ].flat(),
    });

registry
    .category("web_tour.tours")
    .add("test_cash_rounding_halfup_biggest_tax_only_round_cash_method_pay_by_bank_and_cash", {
        steps: () =>
            [
                Chrome.startPoS(),
                Dialog.confirm("Open Register"),

                // Order.
                ProductScreen.addOrderline("random_product", "1"),
                ProductScreen.checkTaxAmount("2.05"),
                ProductScreen.checkRoundingAmountIsNotThere(),
                ProductScreen.checkTotalAmount("15.72"),
                ProductScreen.clickPartnerButton(),
                ProductScreen.clickCustomer("AAAAAA"),
                ProductScreen.clickPayButton(),

                PaymentScreen.totalIs("15.72"),
                PaymentScreen.clickPaymentMethod("Bank"),
                PaymentScreen.clickNumpad("0 . 6 8"),
                PaymentScreen.fillPaymentLineAmountMobile("Bank", "0.68"),
                PaymentScreen.remainingIs("15.04"),
                PaymentScreen.clickPaymentMethod("Cash"),
                PaymentScreen.remainingIs("0.0"),
                PaymentScreen.clickInvoiceButton(),
                PaymentScreen.clickValidate(),

                ReceiptScreen.receiptAmountTotalIs("15.72"),
                ReceiptScreen.receiptRoundingAmountIs("0.01"),
                ReceiptScreen.receiptToPayAmountIs("15.73"),
                ReceiptScreen.receiptChangeAmountIsNotThere(),
                ReceiptScreen.clickNextOrder(),

                // Refund.
                Chrome.clickOrders(),
                TicketScreen.selectFilter("Active"),
                TicketScreen.selectFilter("Paid"),
                TicketScreen.selectOrder("0001"),
                TicketScreen.confirmRefund(),

                ProductScreen.checkTaxAmount("-2.05"),
                ProductScreen.checkRoundingAmountIsNotThere(),
                ProductScreen.checkTotalAmount("-15.72"),
                ProductScreen.clickPayButton(),

                PaymentScreen.totalIs("-15.72"),
                PaymentScreen.clickPaymentMethod("Bank"),
                PaymentScreen.clickNumpad("0 . 6 8 +/-"),
                PaymentScreen.fillPaymentLineAmountMobile("Bank", "-0.68"),
                PaymentScreen.remainingIs("-15.04"),
                PaymentScreen.clickPaymentMethod("Cash"),
                PaymentScreen.remainingIs("0.0"),
                PaymentScreen.clickValidate(),

                ReceiptScreen.receiptAmountTotalIs("-15.72"),
                ReceiptScreen.receiptRoundingAmountIs("-0.01"),
                ReceiptScreen.receiptToPayAmountIs("-15.73"),
                ReceiptScreen.receiptChangeAmountIsNotThere(),
                ReceiptScreen.clickNextOrder(),
            ].flat(),
    });

registry.category("web_tour.tours").add("test_cash_rounding_with_change", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ProductScreen.addOrderline("random_product", "1"),
            ProductScreen.checkTaxAmount("2.05"),
            ProductScreen.checkRoundingAmount("-0.02"),
            ProductScreen.checkTotalAmount("15.70"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AAAAAA"),
            ProductScreen.clickPayButton(),

            PaymentScreen.totalIs("15.70"),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickNumpad("2 0"),
            PaymentScreen.fillPaymentLineAmountMobile("Bank", "20.00"),
            PaymentScreen.changeIs("4.30"),
            PaymentScreen.clickInvoiceButton(),
            PaymentScreen.clickValidate(),

            ReceiptScreen.receiptAmountTotalIs("15.72"),
            ReceiptScreen.receiptRoundingAmountIs("-0.02"),
            ReceiptScreen.receiptToPayAmountIs("15.70"),
            ReceiptScreen.receiptChangeAmountIs("4.30"),
            ReceiptScreen.clickNextOrder(),
        ].flat(),
});
