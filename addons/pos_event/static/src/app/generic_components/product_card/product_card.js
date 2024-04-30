// Part of Odoo. See LICENSE file for full copyright and licensing details.
import { ProductCard } from "@point_of_sale/app/generic_components/product_card/product_card";
import { patch } from "@web/core/utils/patch";

patch(ProductCard.prototype, {
    get displayRemainingSeats() {
        return Boolean(this.props.product.event_id) && this.props.product.event_id.seats_limited;
    },
});
