odoo.define('website_event.ticket_details', function (require) {
    var publicWidget = require('web.public.widget');

    publicWidget.registry.ticketDetailsWidget = publicWidget.Widget.extend({
        selector: '.o_wevent_js_ticket_details',
        events: {
            'click .o_wevent_registration_btn': '_onTicketDetailsClick',
            'change .custom-select': '_onTicketQuantityChange'
        },
        start: function (){
            this.foldedByDefault = this.$el.data('foldedByDefault') === 1;
            return this._super.apply(this, arguments);
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * @private
         */
        _getTotalTicketCount: function (){
            var ticketCount = 0;
            this.$('.custom-select').each(function (){
                ticketCount += parseInt($(this).val());
            });
            return ticketCount;
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * @private
         * @param {*} ev
         */
        _onTicketDetailsClick: function (ev){
            ev.preventDefault();
            if (this.foldedByDefault){
                $(ev.currentTarget).toggleClass('btn-primary text-left pl-0');
                $(ev.currentTarget).siblings().toggleClass('d-none');
                this.$('.close').toggleClass('d-none');
            }
        },
        /**
         * @private
         */
        _onTicketQuantityChange: function (){
            this.$('button.btn-primary').attr('disabled', this._getTotalTicketCount() === 0);
        }
    });

return publicWidget.registry.ticketDetailsWidget;
});
