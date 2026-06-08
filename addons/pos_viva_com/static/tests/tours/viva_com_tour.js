/* global posmodel */

import * as FeedbackScreen from "@point_of_sale/../tests/pos/tours/utils/feedback_screen_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as TicketScreen from "@point_of_sale/../tests/pos/tours/utils/ticket_screen_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import { registry } from "@web/core/registry";
import * as PaymentScreenViva from "./utils/payment_screen_viva_com_util";

const mockVivaWebhook = () => ({
    content: "Waiting for Viva payment to be processed",
    trigger: ".paymentline_status_title",
    run: async function () {
        const payment_terminal =
            posmodel.getPendingPaymentLine("viva_com").payment_method_id.payment_interface;

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
            PaymentScreen.clickSendButton(),
            mockVivaWebhook(),
            FeedbackScreen.isShown(),
            FeedbackScreen.clickNextOrder(),
            Chrome.clickOrders(),
            TicketScreen.selectFilter("Paid"),
            TicketScreen.selectOrder("0001"),
            TicketScreen.confirmRefund(),
            PaymentScreen.isShown(),
            PaymentScreen.clickPaymentMethod("Viva"),
            PaymentScreen.clickRefundButton(),
            mockVivaWebhook(),
            FeedbackScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("VivaComKioskTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Desk Pad", "1", "5.1", "5.1"),
            ProductScreen.clickPayButton(),
            PaymentScreen.isShown(),
            ...PaymentScreenViva.simulateKioskNamelessCashier(),
            PaymentScreen.clickPaymentMethod("Viva"),
            PaymentScreen.isShown(),
        ].flat(),
});
