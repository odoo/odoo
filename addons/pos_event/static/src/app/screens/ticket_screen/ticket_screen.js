// Part of Odoo. See LICENSE file for full copyright and licensing details.
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { EventTicketButton } from "@pos_event/app/screens/ticket_screen/event_ticket_button/event_ticket_button";
import { patch } from "@web/core/utils/patch";

patch(TicketScreen.prototype, {
    orderHasEventRegistration() {
        return this._selectedSyncedOrder?.lines.some(
            (line) => line.event_registration_ids.length > 0
        );
    },
});

patch(TicketScreen, {
    components: { ...TicketScreen.components, EventTicketButton },
});
