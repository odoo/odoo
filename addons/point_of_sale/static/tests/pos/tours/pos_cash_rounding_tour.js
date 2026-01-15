import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";
import * as TicketScreen from "@point_of_sale/../tests/pos/tours/utils/ticket_screen_util";
import { registry } from "@web/core/registry";

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

                PaymentScreen.isShown(),
                PaymentScreen.clickBack(),

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

                PaymentScreen.isShown(),
                PaymentScreen.clickBack(),

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

                PaymentScreen.isShown(),
                PaymentScreen.clickBack(),

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

                PaymentScreen.isShown(),
                PaymentScreen.clickBack(),

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
