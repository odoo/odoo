/** @odoo-module **/
    import publicWidget from "@web/legacy/js/public/public_widget";

    publicWidget.registry.ticketDetailsWidget = publicWidget.Widget.extend({
        selector: '.o_wevent_js_ticket_details',
        events: {
            'change .form-select': '_onTicketQuantityChange'
        },
        start: function (){
            this.foldedByDefault = this.el.dataset.foldedByDefault === 1;
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
            const selects = this.el.querySelectorAll('.form-select');
            selects.forEach(function (select){
                ticketCount += parseInt(select.value);
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
            var ticketQuantityChangebtn = this.el.querySelector('button.btn-primary');
            ticketQuantityChangebtn.disabled = this._getTotalTicketCount() === 0;
        }
    });

export default publicWidget.registry.ticketDetailsWidget;
