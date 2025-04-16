// Part of Odoo. See LICENSE file for full copyright and licensing details.
import { ProductCard } from "@point_of_sale/app/components/product_card/product_card";
import { patch } from "@web/core/utils/patch";

const { DateTime } = luxon;

patch(ProductCard.prototype, {
    get displayRemainingSeats() {
        return Boolean(this.props.product.event_id);
    },
    get isEventMultiSlot() {
        return Boolean(this.props.product.event_id) && this.props.product.event_id.is_multi_slots;
    },
    get totalFutureSlots() {
        return (
            this.props.product.event_id?.event_slot_ids?.filter(
                (slot) => slot.start_datetime > DateTime.now()
            )?.length || 0
        );
    },
    get totalTicketSeats() {
        const event = this.props.product.event_id;
        const eventTickets = event?.event_ticket_ids;

        if (
            !eventTickets?.length ||
            (!event.seats_limited && eventTickets?.some((ticket) => ticket.seats_max === 0))
        ) {
            return 0;
        }
        if (event.seats_limited && !event.seats_max) {
            return -1;
        }
        return eventTickets.reduce((acc, ticket) => acc + ticket.seats_available, 0) || -1;
    },
});
