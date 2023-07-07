/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { _t } from "@web/core/l10n/translation";

import { useService } from "@web/core/utils/hooks";

patch(ProductScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.notification = useService("pos_notification");
    },
    switchCategory(categoryId) {
        //remove sub category when an event was selected and we change category
        this.state.selectedEventId = null;
        super.switchCategory(...arguments);
    },
    get productsToDisplay(){
        if (this.selectedCategoryId === -1) {
            if (!this.state.selectedEventId) {
                return this.pos.events;
            } else {
                return this.pos.event_tickets.filter(ticket => ticket.event_id[0] === this.state.selectedEventId)
            }
        }
        return super.productsToDisplay;
    },
    getDisplayName(event) {
        if (this.selectedCategoryId === -1){
            return event.name
        }
        return super.getDisplayName(...arguments);
    },
    getImageUrl(event) {
        if (this.selectedCategoryId === -1){
            if (this.state.selectedEventId){
                const selectedEvent = this.getEventSelected();
                return `/web/image?model=event.event&id=${selectedEvent.id}&field=image&unique=${selectedEvent.write_date}`;
            } else {
            return `/web/image?model=event.event&id=${event.id}&field=image&unique=${event.write_date}`;
            }
        }
        return super.getImageUrl(...arguments);
    },
    getPrice(product) {
        if (this.selectedCategoryId === -1){
            if (!this.state.selectedEventId) {
                return `From ${this.env.utils.formatCurrency(Math.min(...this.pos.event_tickets.filter(ticket => ticket.event_id[0] === product.id).map(product => product.price)))}`
            } else {
                return this.env.utils.formatCurrency(product.price)
            }
        }
        return super.getPrice(...arguments);
    },
    async onClickProduct(product) {
        if (this.selectedCategoryId === -1){
            if (!this.state.selectedEventId) {
                this.state.selectedEventId = product.id
            } else {
                const currentOrder = this.pos.get_order();
                const options = {
                    price : product.price, //- this.pos.db.get_product_by_id(product.product_id[0]).lst_price,
                    extras: {
                        price_type: "automatic",
                    },
                    ticketId: product.id,
                    eventId: product.event_id[0],
                }
                if (product.seats_available - this.pos.get_order().getTicketOrderQuantity()[product.id] <= 0){
                    this.notification.add(
                        _t(
                            "This ticket is SOLD-OUT"
                        ),
                    );
                } else{
                    currentOrder.add_product(this.pos.db.get_product_by_id(product.product_id[0]), options);
                }
            }
        } else {
        super.onClickProduct(...arguments);
        }
    },
    getEventSelected() {
        if (this.state.selectedEventId) {
            return this.pos.events.find(event => event.id === this.state.selectedEventId)
        }
        return null;
    },
    isEventSelected() {
        if (this.selectedCategoryId === -1 && !this.state.selectedEventId){
            return true;
        }
        return false;
    },
    getAvalibleSeats(product) {
        if (!('seats_available' in product)) {
            return null
        } else {
            const result = product.seats_available - this.pos.get_order().getTicketOrderQuantity()[product.id]
            return result
        }
    }
});
