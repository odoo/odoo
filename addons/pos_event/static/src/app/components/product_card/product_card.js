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
                (slot) =>
                    slot.start_datetime > DateTime.now() &&
                    (!slot.event_id.seats_limited || slot.seats_available)
            )?.length || 0
        );
    },
    get totalAvailableSeats() {
        const event = this.props.product.event_id;
        const eventTickets = event?.event_ticket_ids;
        const hasUnlimitedTickets = eventTickets?.some((ticket) => ticket.seats_max === 0);
        const ticketsSeatsAvailable = eventTickets?.reduce(
            (acc, ticket) => acc + ticket.seats_available,
            0
        );

        // Event = unlimited seats, Tickets = total is unlimited
        if (!eventTickets?.length || (!event.seats_limited && hasUnlimitedTickets)) {
            return 0;
        }
        // Event = limited seats, Tickets = total is unlimited
        if (event.seats_limited && hasUnlimitedTickets) {
            return event.seats_available || -1;
        }
        // Event = unlimited seats, Tickets = total is limited
        if (!event.seats_limited && !hasUnlimitedTickets) {
            return ticketsSeatsAvailable || -1;
        }
        // Event = limited seats, Tickets = total is limited
        return Math.min(event.seats_available, ticketsSeatsAvailable) || -1;
    },
});
