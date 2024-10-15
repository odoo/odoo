// Part of Odoo. See LICENSE file for full copyright and licensing details.
import { ProductCard } from "@point_of_sale/app/generic_components/product_card/product_card";
import { patch } from "@web/core/utils/patch";

patch(ProductCard.prototype, {
    get displayRemainingSeats() {
        return Boolean(this.props.product.event_id);
    },
    get totalTicketSeats() {
        return (
            this.props.product.event_id?.event_ticket_ids?.reduce(
                (acc, ticket) => acc + ticket.seats_available,
                0
            ) || 0
        );
    },
});
