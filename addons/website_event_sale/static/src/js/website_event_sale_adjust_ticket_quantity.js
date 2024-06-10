/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';
import { WebsiteEventTicketRegistrationDialog } from "@website_event/client_action/website_event_ticket_registration_dialog";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.adjustTicketQuantityWidget = publicWidget.Widget.extend({
    selector: '.oe_cart',
    events: {
        'click .o_wevent_sale_adjust_ticket_quantity': '_onAdjustQuantity',
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------
    /**
     * @private
     */
    _onAdjustQuantity: async function (ev) {
        const eventSlug = ev.currentTarget.dataset.eventSlug;
        const registrationId = ev.currentTarget.dataset.registrationId;
        const data = await rpc(`/event/${eventSlug}/registration/modify`, {
            registration_id: parseInt(registrationId)
        })
        this.call("dialog", "add", WebsiteEventTicketRegistrationDialog, {data: data});
    }
});

export default {
    adjustTicketQuantityWidget: publicWidget.registry.adjustTicketQuantityWidget,
};
