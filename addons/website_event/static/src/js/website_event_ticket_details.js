odoo.define('website_event.ticket_details', function (require) {
    var publicWidget = require('web.public.widget');

    publicWidget.registry.ticketDetailsWidget = publicWidget.Widget.extend({
        selector: '.o_wevent_js_ticket_details',
        events: {
            'click .o_wevent_registration_btn': '_onTicketDetailsClick',
            'change .form-select': '_onTicketQuantityChange'
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
            this.$('.form-select').each(function (){
                ticketCount += parseInt($(this).val());
            });
            return ticketCount;
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * When the "Fold Tickets Details" option is active, this will be called each
         * time the user expand or fold the tickets (o_wevent_registration_btn). This
         * allows to show/hide elements depending on the folding state.
         *
         * @private
         * @param {*} ev
         */
        _onTicketDetailsClick: function (ev){
            ev.preventDefault();
            if (this.foldedByDefault){
                let $target = $(ev.currentTarget);
                $target.toggleClass('btn-primary');
                $target.children().toggleClass('d-none');
                $target.siblings('.o_wevent_registration_title, .o_wevent_price_range').toggleClass('d-none');
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
