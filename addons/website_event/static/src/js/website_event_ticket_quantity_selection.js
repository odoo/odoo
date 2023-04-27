/** @odoo-module */

import core from 'web.core';
import publicWidget from 'web.public.widget';

/**
 * This widget can be hooked to a select tag in order to send an
 * "event_ticket_quantity_change" event each time the selection is changed.
 * The event payload contains ticketId:{integer}, quantity:{integer}.
 *
 * @param ticketId id of the ticket to which the selection refers
 */
export const EventTicketQuantitySelectionWidget = publicWidget.Widget.extend({
    selector: '.o_event_ticket_quantity_selection',
    events: {
        'change': '_onQuantityChange',
    },

    start: function () {
        this.ticketId = this.$el.data('ticketId');
        // Note that ticketInitQuantity must be identical to the one transmitted to the price widget
        const initQuantity = this.$el.data('ticketInitQuantity') || 0;
        this.$el.val(initQuantity.toString());
    },

    _onQuantityChange: function (ev) {
        core.bus.trigger('event_ticket_quantity_change', {
            ticketId: this.ticketId,
            quantity: parseInt(ev.target.value)
        });
    },
});

publicWidget.registry.EventTicketQuantitySelectionWidget = EventTicketQuantitySelectionWidget;
