odoo.define('point_of_sale.TicketButton', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class TicketButton extends PosComponent {
        onClick() {
            if (this.props.isTicketScreenShown) {
                this.env.posbus.trigger('ticket-button-clicked');
            } else {
                this.showScreen('TicketScreen');
            }
        }
        get count() {
            if (this.env.pos) {
                return this.env.pos.get_order_list().length;
            } else {
                return 0;
            }
        }
    }
    TicketButton.template = 'TicketButton';

    Registries.Component.add(TicketButton);

    return TicketButton;
});
