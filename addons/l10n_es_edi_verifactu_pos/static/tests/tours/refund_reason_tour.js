import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";
import * as TicketScreen from "@point_of_sale/../tests/pos/tours/utils/ticket_screen_util";
import { registry } from "@web/core/registry";

// The order being refunded is created directly through the backend (see test_frontend.py)
// instead of being sold through this tour: it keeps the tour focused on the refund
// interaction under test, and avoids depending on the session's order numbering to find it.

// A PoS order that is not explicitly invoiced is a simplified invoice: refunding it must
// automatically use Veri*Factu reason R5, without asking the cashier to pick one.
registry.category("web_tour.tours").add("l10n_es_edi_verifactu_pos.tour_refund_not_invoiced", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ...ProductScreen.clickRefund(),
            TicketScreen.selectOrderByPrice("121.00"),
            ProductScreen.clickNumpad("1"),
            TicketScreen.toRefundTextContains("To Refund: 1.00"),
            TicketScreen.confirmRefund(),
            Dialog.isNot(),
            PaymentScreen.isShown(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            Chrome.endTour(),
        ].flat(),
});

// A PoS order that was explicitly invoiced is not a simplified invoice: refunding it must
// let the cashier pick a Veri*Factu reason through the popup.
registry.category("web_tour.tours").add("l10n_es_edi_verifactu_pos.tour_refund_invoiced", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ...ProductScreen.clickRefund(),
            TicketScreen.selectOrderByPrice("121.00"),
            ProductScreen.clickNumpad("1"),
            TicketScreen.toRefundTextContains("To Refund: 1.00"),
            TicketScreen.confirmRefund(),
            Dialog.is({ title: "Additional Refund Information" }),
            {
                content: "select Veri*Factu refund reason R2",
                trigger: "select#verifactu_refund_reason",
                run: "select R2",
            },
            Dialog.confirm("Ok"),
            PaymentScreen.isShown(),
            // The refund is automatically forced "To Invoice" since the refunded order
            // was invoiced (point_of_sale core): no need to click the Invoice button again.
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            Chrome.endTour(),
        ].flat(),
});
