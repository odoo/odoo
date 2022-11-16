/** @odoo-module alias=pos_event.EventConfiguratorPopup */

import Registries from 'point_of_sale.Registries';
import AbstractAwaitablePopup from 'point_of_sale.AbstractAwaitablePopup';
const { useRef, useState } = owl;

/**
 * props = {
 *  eventData : [{
 *      event: {
 *          'id', 'name', 'event_registrations_open', 'date_begin', 'date_end',
 *           tickets: {'id', 'name', 'description', 'sale_available', 'event_id', 'product_id'}
 *      }
 *  }]
 * }
 */
export class EventConfiguratorPopup extends AbstractAwaitablePopup  {
    setup() {
        super.setup();
        const openEvents = this.props.eventData.filter(data => data['event_registrations_open']);
        this.ticketsRef = Object.fromEntries(openEvents.map(data => [data['id'], useRef(`${data['id']}-tickets`)]));
        this.state = useState(Object.fromEntries(openEvents.map(data => [
            data['id'], Object.fromEntries(data['tickets'].map(ticket => [ticket['id'], 0]))
        ])));
        this.currentEventId = null;
    }
    _resetEventTickets(eventId) {
        for (const ticketId in this.state[eventId]) {
            this.state[eventId][ticketId] = 0;
        }
    }
    _onEventClick(eventId) {
        if (this.currentEventId === eventId) {
            this.ticketsRef[eventId].el.classList.remove('open');
            this.currentEventId = null;
            this._resetEventTickets(eventId)
        } else {
            if (this.currentEventId) {
                this.ticketsRef[this.currentEventId].el.classList.remove('open');
                this._resetEventTickets(this.currentEventId);
            }
            this.ticketsRef[eventId].el.classList.add('open');
            this.currentEventId = eventId;
        }
    }
    _onInputKeyPress(event) {
        if (event.key.toLowerCase() === 'e' ) {
            event.preventDefault();
        }
    }
    _onMinusClick(eventId, ticketId) {
        this.state[eventId][ticketId] = Math.max(0, this.state[eventId][ticketId] - 1);
    }
    _onPlusClick(eventId, ticketId) {
        this.state[eventId][ticketId]++;
    }
    _onDeleteClick(eventId, ticketId) {
        this.state[eventId][ticketId] = 0;
    }
    _canConfirm() {
        if (this.currentEventId) {
            const numberTicket = Object.values(this.state[this.currentEventId]).reduce((a, b) => a + b);
            return numberTicket;
        }
        return false;
    }
};

EventConfiguratorPopup.template = 'EventConfiguratorPopup';
Registries.Component.add(EventConfiguratorPopup);
