odoo.define('point_of_sale.OrderlineCustomerNoteButton', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const { useListener } = require('web.custom_hooks');
    const Registries = require('point_of_sale.Registries');

    class OrderlineCustomerNoteButton extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('click', this.onClick);
        }
        get selectedOrderline() {
            return this.env.pos.get_order().get_selected_orderline();
        }
        async onClick() {
            if (!this.selectedOrderline) return;

            const { confirmed, payload: inputNote } = await this.showPopup('TextAreaPopup', {
                startingValue: this.selectedOrderline.get_customer_note(),
                title: this.env._t('Add Customer Note'),
            });

            if (confirmed) {
                this.selectedOrderline.set_customer_note(inputNote);
            }
        }
    }
    OrderlineCustomerNoteButton.template = 'OrderlineCustomerNoteButton';

    ProductScreen.addControlButton({
        component: OrderlineCustomerNoteButton,
        condition: function() {
            return this.env.pos.config.iface_orderline_customer_notes;
        },
    });

    Registries.Component.add(OrderlineCustomerNoteButton);

    return OrderlineCustomerNoteButton;
});
