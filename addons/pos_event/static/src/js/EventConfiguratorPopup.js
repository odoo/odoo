/** @odoo-module */

import AbstractAwaitablePopup from "@point_of_sale/js/Popups/AbstractAwaitablePopup";
import Registries from "@point_of_sale/js/Registries";
const { useRef, useState, onWillStart} = owl;

/**
 * props = {
 *  eventData : [{
 *      event: {
 *          "id", "name", "event_registrations_open", "date_begin", "date_end", "seats_available"
 *           tickets: [{"id", "name", "description", "sale_available", "event_id", "product_id", "seats_available"}]
 *      }
 *  }]
 * }
 */

export class EventConfiguratorPopup extends AbstractAwaitablePopup  {
    setup() {
        super.setup();
        const openEvents = this.props.eventData.filter(data => data["event_registrations_open"]);
        this.ticketsRef = Object.fromEntries(openEvents.map(data => [data["id"], useRef(`${data["id"]}-tickets`)]));
        this.state = useState({
            eventTickets: Object.fromEntries(openEvents.map(data => [
                data["id"], Object.fromEntries(data["tickets"].map(ticket => [ticket["id"], 0]))
            ])),
            canBeConfirmed: false,
        });
        this.currentEventId = null;
        this.ticketInfoMap = {};
        for (const event of openEvents) {
            for (const ticket of event["tickets"]) {
                this.ticketInfoMap[ticket["id"]] =  {
                    name: ticket["name"],
                    id: ticket["id"],
                    productId: ticket["product_id"],
                    product: this.env.pos.db.get_product_by_id(ticket["product_id"]),
                };
            }
        }
        onWillStart(this._loadMissingTicketPrices);
    }
    //@override
    async getPayload() {
        const eventName = this.props.eventData.find(event => event.id === this.currentEventId).name
        const ticketDetails = []
        for (const id in this.state.eventTickets[this.currentEventId]) {
            const quantity = this.state.eventTickets[this.currentEventId][id];
            if (quantity > 0) {
                const ticketInfo = this.ticketInfoMap[id];
                ticketDetails.push({
                    product: ticketInfo["product"],
                    name: `${ticketInfo["name"]} - ${eventName}`,
                    id: ticketInfo["id"],
                    eventId: this.currentEventId,
                    quantity,
                });
            }
        }
        return { ticketDetails }
    }
    async _loadMissingTicketPrices() {
        const missingProductTicketIds = [];
        const missingProductIds = [];
        for (const info of Object.values(this.ticketInfoMap)) {
            if (!info["product"]) {
                missingProductTicketIds.push(info["id"]);
                missingProductIds.push(info["productId"]);
            }
        }
        if (missingProductIds.length > 0) {
            try {
                await this.env.pos.fetchProductsByIds(missingProductIds);
                for (const ticketId of missingProductTicketIds) {
                    const product = this.env.pos.db.get_product_by_id(this.ticketInfoMap[ticketId]["productId"]);
                    this.ticketInfoMap[ticketId]["product"] = product;
                }
            } catch {
                this.cancel();
                this.showPopup("OfflineErrorPopup", {
                    title: this.env._t("Connection Error"),
                    body: this.env._t("Unable to correctly load missing ticket products."),
                });
            }
        }
    }
    _resetEventTickets(eventId) {
        for (const ticketId in this.state.eventTickets[eventId]) {
            this.state.eventTickets[eventId][ticketId] = 0;
        }
    }
    _onEventClick(eventId) {
        const timeout = 500;
        const currentEventId = this.currentEventId;
        const resetInput = () => this._resetEventTickets(currentEventId);
        if (this.currentEventId === eventId) {
            this.ticketsRef[eventId].el.classList.remove("open");
            this.currentEventId = null;
            setTimeout(resetInput, timeout)
            this.state.canBeConfirmed = false;
        } else {
            if (this.currentEventId) {
                this.ticketsRef[this.currentEventId].el.classList.remove("open");
                setTimeout(resetInput, timeout)
                this.state.canBeConfirmed = false; // trigger the change in the front
            }
            this.ticketsRef[eventId].el.classList.add("open");
            this.currentEventId = eventId;
            this.state.canBeConfirmed = true;
        }
    }
    _onInputKeyPress(event) {
        if (event.key.toLowerCase() === "e" ) {
            event.preventDefault();
        }
    }
    _onMinusClick(eventId, ticketId) {
        this.state.eventTickets[eventId][ticketId] = Math.max(0, this.state.eventTickets[eventId][ticketId] - 1);
    }
    _onPlusClick(eventId, ticketId) {
        this.state.eventTickets[eventId][ticketId]++;
    }
    _onDeleteClick(eventId, ticketId) {
        this.state.eventTickets[eventId][ticketId] = 0;
    }
    _canConfirm() {
        if (this.state.canBeConfirmed && this.currentEventId) {
            const numberTicket = Object.values(this.state.eventTickets[this.currentEventId]).reduce((a, b) => a + b);
            return numberTicket;
        }
        return false;
    }
};

EventConfiguratorPopup.template = "EventConfiguratorPopup";
Registries.Component.add(EventConfiguratorPopup);
