/** @odoo-module alias=pos_event.EventConfiguratorPopup */

import Registries from 'point_of_sale.Registries';
import AbstractAwaitablePopup from 'point_of_sale.AbstractAwaitablePopup';
const { useRef } = owl;

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
        this.ticketsRef = Object.fromEntries(this.props.eventData.filter(data => data['event_registrations_open'])
            .map(data => [data['id'], useRef(`${data['id']}-tickets`)]));
    }
    _toggleEvent(eventId) {
        for (const id in this.ticketsRef) {
            if (id != eventId) {
                this.ticketsRef[id].el.classList.remove('open');
            }
        }
        this.ticketsRef[eventId].el.classList.toggle('open'); // we want the opening effect to be the last
    }
};

EventConfiguratorPopup.template = 'EventConfiguratorPopup';
Registries.Component.add(EventConfiguratorPopup);
