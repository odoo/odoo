import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/utils/receipt_screen_util";
import * as TicketScreen from "@point_of_sale/../tests/tours/utils/ticket_screen_util";
import { registry } from "@web/core/registry";

// A PoS order invoiced automatically as a simplified invoice (l10n_es_pos, no identified
// customer) is not a real invoice: refunding it must automatically use TicketBAI reason R5,
// without asking the cashier to pick one.
registry.category("web_tour.tours").add("l10n_es_edi_tbai_pos.tour_refund_simplified_invoice", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("tbai_pos_product"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.remainingIs("0.00"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            ReceiptScreen.clickNextOrder(),
            // refund
            ...ProductScreen.clickRefund(),
            TicketScreen.selectOrder("-0001"),
            ProductScreen.clickNumpad("1"),
            TicketScreen.toRefundTextContains("To Refund: 1.00"),
            TicketScreen.confirmRefund(),
            Dialog.isNot(),
            ProductScreen.isShown(),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            Chrome.endTour(),
        ].flat(),
});

// A PoS order explicitly invoiced to an identified customer is not a simplified invoice:
// refunding it must let the cashier pick a TicketBAI reason through the popup.
registry.category("web_tour.tours").add("l10n_es_edi_tbai_pos.tour_refund_explicit_invoice", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("tbai_pos_product"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.inputCustomerSearchbar("partner_b"),
            ProductScreen.clickCustomer("partner_b"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickInvoiceButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.remainingIs("0.00"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            ReceiptScreen.clickNextOrder(),
            // refund
            ...ProductScreen.clickRefund(),
            TicketScreen.selectOrder("-0001"),
            ProductScreen.clickNumpad("1"),
            TicketScreen.toRefundTextContains("To Refund: 1.00"),
            TicketScreen.confirmRefund(),
            Dialog.is({ title: "Additional Refund Information" }),
            {
                content: "select TicketBAI refund reason R2",
                trigger: "select#tbai_refund_reason",
                run: "select R2",
            },
            Dialog.confirm("Ok"),
            ProductScreen.isShown(),
            // The refund is already flagged to be invoiced (set alongside the refund
            // reason): no need to click the Invoice button again here.
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            Chrome.endTour(),
        ].flat(),
});
