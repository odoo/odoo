import { OrdersHistoryPage } from "@pos_self_order/app/pages/order_history_page/order_history_page";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { browser } from "@web/core/browser/browser";

patch(OrdersHistoryPage.prototype, {
    async setup() {
        super.setup();
        this.notification = useService("notification");
    },

    async downloadOrderTickets(line) {
        try {
            const ticketInfo = await rpc("/pos-self-order/get-event-registrations-data", {
                access_token: this.selfOrder.access_token,
                order_id: line.order_id.id,
                event_ticket_id: line.event_ticket_id?.id,
            });

            const { event_id, registration_ids, tickets_hash } = ticketInfo;
            const url = `/event/${event_id}/my_tickets?registration_ids=${JSON.stringify(
                registration_ids
            )}&tickets_hash=${tickets_hash}`;
            browser.open(url, "_blank");
        } catch (error) {
            console.error(error);
            this.notification.add(_t("Unable to download your ticket. Something went wrong"), {
                type: "danger",
            });
        }
    },
});
