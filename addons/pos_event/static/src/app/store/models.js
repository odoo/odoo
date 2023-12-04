/** @odoo-module */
"use strict";

import { patch } from "@web/core/utils/patch";
import { Order, Orderline } from "@point_of_sale/app/store/models";
import { _t } from "@web/core/l10n/translation";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { ask } from "@point_of_sale/app/store/make_awaitable_dialog";

patch(Order.prototype, {
    //@override
    set_orderline_options(orderline, options) {
        super.set_orderline_options(...arguments);
        if (options.ticketId) {
            orderline.setEventData(options.ticketId, options.eventId);
        }
        return orderline;
    },
    hasEventLines() {
        const hasEventLines = this.get_orderlines().some(line => line.eventId);
        return hasEventLines;
    },
    async pay() {
        const order = this.pos.get_order();
        if (order.hasEventLines() && !order.get_partner()) {
            const confirmed = await ask(this.env.services.dialog, {
                title: _t("Customer needed"),
                body: _t("Buying event ticket requires a customer to be selected"),
            });
            if (confirmed) {
                const { confirmed, payload: newPartner } = await this.pos.env.services.pos.showTempScreen(
                    "PartnerListScreen",
                    { partner: null }
                );
                if (confirmed) {
                    // todo refactor set_partner with updatePricelist in the whole pos
                    order.set_partner(newPartner);
                    order.updatePricelistAndFiscalPosition(newPartner);
                }
            }
        } else {
            this.setTicketOrder();
            return super.pay(...arguments);
        }
    },
    async setTicketOrder(){
        const eventLines = this.get_orderlines().filter(line => line.eventId);
        if (eventLines.length > 0) {
            const registrationVals = [];
            const partnerId = this.get_partner().id;
            //  In case we have a situation where we have one orderline with a qty of 2
            //  and one orderline with a qty of -1, we should create only one registration in total.
            //  We create a counter for every ticket to know exactly how many registration need to be made
            const tickedIdCounter = {};
            for (const line of eventLines) {
                if (line.eventTicketId in tickedIdCounter) {
                    tickedIdCounter[line.eventTicketId] += line.quantity;
                } else {
                    tickedIdCounter[line.eventTicketId] = line.quantity
                }
            }
            // We create the registrations values based on the counter.
            let remainingCounter = { ...tickedIdCounter };
            for (const line of eventLines) {
                const registrationQty = remainingCounter[line.eventTicketId] - line.quantity >= 0 ? line.quantity : remainingCounter[line.eventTicketId];
                remainingCounter[line.eventTicketId] -= registrationQty;
                for (let i = 0; i < registrationQty; i++) {
                    registrationVals.push({
                        event_id: line.eventId,
                        event_ticket_id: line.eventTicketId,
                        partner_id: partnerId,
                        state: "draft",
                    });
                }
            }
            //todo improve registration in the event app because this doesn"t take concurrency problem into account ...
            const registrationIds = await this.pos.orm.create("event.registration",registrationVals)

            // Assigning the registration ids to the order lines using the same mechanism as above. Since we are
            // using array which are ordered, the received ids can be attributed using the same order
            remainingCounter = { ...tickedIdCounter };
            const remainingRegistrationIds = [...registrationIds];
            for (const line of eventLines) {
                const registrationQty = remainingCounter[line.eventTicketId] - line.quantity >= 0 ? line.quantity : remainingCounter[line.eventTicketId];
                remainingCounter[line.eventTicketId] -= registrationQty;
                const registrationToSet = remainingRegistrationIds.splice(0, registrationQty);
                if (registrationToSet.length > 0) {
                    line.setEventRegistrationIds(registrationToSet);
                }
            }
        }
    },
    getTicketOrderQuantity(){
        const result= Object.fromEntries(this.pos.event_tickets.map(ticket => [ticket["id"], 0]));
        this.orderlines.forEach((orderline) => { result[orderline.eventTicketId ] += orderline.quantity });
        return result;
    },

});

patch(Orderline.prototype, {
    // constructor() {
    //     super(...arguments);
    //     this.eventTicketId = this.eventTicketId || null;
    // }
    //@override
    clone(){
        const orderline = super.clone(...arguments);
        orderline.ticketId = this.ticketId;
        orderline.eventId = this.eventId;
        return orderline;
    },
    //@override
    export_as_JSON(){
        const json = super.export_as_JSON(...arguments);
        json.event_ticket_id  = this.eventTicketId;
        json.event_id = this.eventId;
        json.event_registration_ids = this.eventRegistrationIds;
        return json;
    },
    //@override
    init_from_JSON(json){
        super.init_from_JSON(...arguments);
        this.eventTicketId = json.event_ticket_id;
        this.eventId = json.event_id;
        this.eventRegistrationIds = json.event_registration_ids;
    },
    setEventData(ticketId, eventId) {
        this.eventTicketId = ticketId;
        this.eventId = eventId;
    },
    setEventRegistrationIds(ids) {
        this.eventRegistrationIds = ids;
    },
    can_be_merged_with(orderline) {
        const result = super.can_be_merged_with(...arguments);
        if(this.eventId){
            return result && this.eventTicketId === orderline.eventTicketId;
        }
        return result

    },
    get_full_product_name() {
        if (this.eventId){
            const event_ticket = this.pos.event_tickets.find(ticket => ticket.id === this.eventTicketId);
            return `${event_ticket.name} - ${event_ticket.event_id[1]}`;
        }
        return super.get_full_product_name(...arguments);
    }
});

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
    },
    async _processData(loadedData) {
        await super._processData(...arguments);
        this.events = loadedData['event.event'];
        this._loadEventTicket(loadedData['event.event.ticket']);
    },
    _loadEventTicket(tickets) {
        this.event_tickets = tickets;
        //Display the image of the events on their linked tickets
        if (tickets){
            this.event_tickets.forEach(ticket => ticket['image_128'] = this.events.find(event => event.id === ticket.event_id[0]).image_128)
        }
    },
    async getProductInfo(product, quantity) {
        if (product.event_id) {
            const info = await super.getProductInfo(this.db.get_product_by_id(product.product_id[0]), 1);
            const [eventData] = await this.orm.read(
                "event.event",
                [product.event_id[0]],
                [
                    "name",
                    "date_begin",
                    "date_end",
                    "address_inline",
                ]
            );
            info['eventData'] = eventData;
            return info
        }
        return await super.getProductInfo(...arguments);

    }
});
