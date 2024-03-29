/** @odoo-module **/
    import publicWidget from "@web/legacy/js/public/public_widget";

    publicWidget.registry.ticketDetailsWidget = publicWidget.Widget.extend({
        selector: '.o_wevent_js_ticket_details',
        events: {
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
         * @private
         */
        _onTicketQuantityChange: function (){
            this.$('button.btn-primary').attr('disabled', this._getTotalTicketCount() === 0);
        }
    });

export default publicWidget.registry.ticketDetailsWidget;
