odoo.define('point_of_sale.OrderlineCustomerNoteButton', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const { useListener } = require("@web/core/utils/hooks");
    const Registries = require('point_of_sale.Registries');

    class OrderlineCustomerNoteButton extends PosComponent {
        setup() {
            super.setup();
            useListener('click', this.onClick);
        }
        async onClick() {
            const selectedOrderline = this.env.pos.get_order().get_selected_orderline();
            if (!selectedOrderline) return;

            const { confirmed, payload: inputNote } = await this.showPopup('TextAreaPopup', {
                startingValue: selectedOrderline.get_customer_note(),
                title: this.env._t('Add Customer Note'),
            });

            if (confirmed) {
                selectedOrderline.set_customer_note(inputNote);
            }
        }
    }
    OrderlineCustomerNoteButton.template = 'OrderlineCustomerNoteButton';

    ProductScreen.addControlButton({
        component: OrderlineCustomerNoteButton,
    });

    Registries.Component.add(OrderlineCustomerNoteButton);

    return OrderlineCustomerNoteButton;
});
