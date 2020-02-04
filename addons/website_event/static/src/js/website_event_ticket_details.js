odoo.define('website_event.ticket_details', function (require) {
    var publicWidget = require('web.public.widget');

    publicWidget.registry.ticketDetailsWidget = publicWidget.Widget.extend({
        selector: '.o_wevent_js_ticket_details',
        events: {
            'click .o_wevent_registration_btn': '_onTicketDetailsClick',
        },
        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------
        _onTicketDetailsClick: function (ev){
            $(ev.currentTarget).toggleClass('btn-primary text-left pl-0');
            $(ev.currentTarget).siblings().toggleClass('d-none');
        },
    });

return publicWidget.registry.ticketDetailsWidget;
});
