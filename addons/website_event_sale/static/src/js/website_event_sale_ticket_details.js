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
            Array.from(ev.currentTarget.parentNode.children).forEach(child => {
                if (child !== ev.currentTarget) {
                    child.classList.toggle('collapse');
                }
            });
        }
    }
});
