/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';

publicWidget.registry.ticketDetailsWidget.include({
    /**
     * Overriding the method to toggle the tickets registration
     * pricelist dropdown visibility on ticket details click
     */
    _onTicketDetailsClick: function(ev) {
        this._super(...arguments);
        if (this.foldedByDefault){
            $(ev.currentTarget).siblings('#o_wevent_tickets_pricelist').toggleClass('collapse');
        }
    }
});
