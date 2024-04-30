// Part of Odoo. See LICENSE file for full copyright and licensing details.
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
    can_be_merged_with(orderline) {
        return (
            this.event_ticket_id?.id === orderline.event_ticket_id?.id &&
            super.can_be_merged_with(...arguments)
        );
    },
    set_quantity(quantity, keep_price) {
        const eventSeats = this.event_ticket_id?.event_id?.seats_available;
        const ticketSeats = this.event_ticket_id?.seats_available;

        if (
            (eventSeats < parseInt(quantity) && this.event_ticket_id?.event_id?.seats_limited) ||
            (ticketSeats < parseInt(quantity) && this.event_ticket_id?.seats_max !== 0)
        ) {
            return {
                title: _t("Not enough seats available"),
                body: _t(
                    "There are not enough seats available for this event. Please select a lower quantity."
                ),
            };
        }

        return super.set_quantity(quantity, keep_price);
    },
});
