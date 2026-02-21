import { ProductCard } from "@pos_self_order/app/components/product_card/product_card";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(ProductCard.prototype, {
    get ticketAvailabilityText() {
        const event = this.props.product.event_id;
        const noOfSlots = event?.event_slot_ids?.length || 0;

        if (noOfSlots) {
            return `${noOfSlots} ${_t("slots available")}`;
        }

        const tickets = event.event_ticket_ids || [];
        if (!event.seats_limited && tickets.some((t) => !t.seats_max && !t.seats_available)) {
            return _t("Unlimited Seats");
        }

        const sum = tickets.reduce((acc, t) => acc + (t.seats_available || 0), 0);
        const seats = event.seats_limited
            ? Math.min(event.seats_available || 0, sum || 0)
            : sum || 0;

        if (seats > 0) {
            return `${seats} ${_t("seats available")}`;
        }
        return _t("Sold out");
    },
});
