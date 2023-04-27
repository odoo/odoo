/** @odoo-module */

import core from 'web.core';
import publicWidget from 'web.public.widget';

/**
 * This widget displays the event ticket price and refresh it when an event "event_ticket_quantity_change" is fired
 * concerning the ticket given as parameter.
 *
 * @param: {integer} ticketId id of the ticket for which the price will be rendered
 */
export const EventSaleTicketPriceWidget = publicWidget.Widget.extend({
    selector: '.o_event_sale_ticket_price',
    events: {},

    start: async function () {
        await this._super.apply(this, arguments);
        this.ticketId = this.$el.data('ticketId');
        this.ready = false;
        this.data = null;
        core.bus.on('event_ticket_quantity_change', this, this._quantity_change);
        // Note that ticketInitQuantity must be identical to the one transmitted to the quantity selection widget
        const initQuantity = this.$el.data('ticketInitQuantity');
        return this._update(initQuantity || 0);
    },

    _quantity_change: function (data) {
        if (data.ticketId === this.ticketId) {
            this._update(data.quantity);
        }
    },

    _update: async function (quantity) {
        this.data = await this._rpc({
            route: `/website_event_sale/ticket/${this.ticketId}/unit_price/render`,
            params: { quantity },
        });
        this.ready = true;
        this.el.innerHTML = this.data;
    },
});

publicWidget.registry.EventSaleTicketPrice = EventSaleTicketPriceWidget;
