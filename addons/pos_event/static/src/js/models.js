odoo.define('pos_restaurant.models', function (require) {
"use strict";

const { Order, Orderline } = require('point_of_sale.models');
const Registries = require('point_of_sale.Registries');
const core = require('web.core');



// New orders are now associated with the current table, if any.
const PosEventOrder = (Order) => class PosEventOrder extends Order {
    //@override
    set_orderline_options(orderline, options) {
        super.set_orderline_options(...arguments);
        if (options.ticketId) {
            orderline.setEventTicketId(options.ticketId)
        }
    }

}
Registries.Model.extend(Order, PosEventOrder);


const PosEventOrderline = (Orderline) => class PosEventOrderline extends Orderline {
    // constructor() {
    //     super(...arguments);
    //     this.eventTicketId = this.eventTicketId || null;
    // }
    // //@override
    // can_be_merged_with(orderline) {
    //     if (orderline.get_note() !== this.get_note()) {
    //         return false;
    //     } else {
    //         return (!this.mp_skip) && (!orderline.mp_skip) && super.can_be_merged_with(...arguments);
    //     }
    // }
    //@override
    clone(){
        const orderline = super.clone(...arguments);
        orderline.ticketId = this.ticketId;
        return orderline;
    }
    //@override
    export_as_JSON(){
        const json = super.export_as_JSON(...arguments);
        json.event_ticket_id  = this.eventTicketId;
    }
    //@override
    init_from_JSON(json){
        super.init_from_JSON(...arguments);
        this.eventTicketId = json.event_ticket_id;
    }
    setEventTicketId(id) {
        this.eventTicketId = id;
    }
}
Registries.Model.extend(Orderline, PosEventOrderline);

});
