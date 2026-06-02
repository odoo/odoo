/* global posmodel */

import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";
import * as TicketScreen from "@point_of_sale/../tests/pos/tours/utils/ticket_screen_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import { registry } from "@web/core/registry";

const mockVivaWebhook = () => ({
    content: "Waiting for Viva payment to be processed",
    trigger: ".electronic_status",
    run: async function () {
        const payment_terminal =
            posmodel.getPendingPaymentLine("viva_com").payment_method_id.payment_terminal;

        // ==> pretend to be viva and send the notification to the POS
        const resp = await fetch(
            `/pos_viva_com/notification?company_id=${payment_terminal.pos.company.id}&token=viva_com_test`,
            {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    EventData: {
                        TerminalId: "01234543210",
                        MerchantTrns: `123/${odoo.pos_session_id}`,
                    },
                    EventTypeId: 1796,
                }),
            }
        );
        if (!resp.ok) {
            throw new Error("Failed to notify Viva webhook");
        }
    },
});

registry.category("web_tour.tours").add("VivaComTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Desk Pad", "1", "5.1", "5.1"),
            ProductScreen.clickPayButton(),
            PaymentScreen.isShown(),
            PaymentScreen.clickPaymentMethod("Viva"),
            mockVivaWebhook(),
            ReceiptScreen.isShown(),
            ReceiptScreen.clickNextOrder(),
            Chrome.clickOrders(),
            TicketScreen.selectFilter("Paid"),
            TicketScreen.selectOrder("0001"),
            TicketScreen.confirmRefund(),
            PaymentScreen.isShown(),
            PaymentScreen.clickPaymentMethod("Viva"),
            {
                content: "Click Refund",
                trigger: "div.button:contains('Refund')",
                run: "click",
            },
            mockVivaWebhook(),
            ReceiptScreen.isShown(),
        ].flat(),
});
