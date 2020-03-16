odoo.define('point_of_sale.OrderlineNoteButton', function(require) {
    'use strict';

    const { PosComponent } = require('point_of_sale.PosComponent');
    const { ProductScreen } = require('point_of_sale.ProductScreen');
    const { useListener } = require('web.custom_hooks');
    const Registry = require('point_of_sale.ComponentsRegistry');

    class OrderlineNoteButton extends PosComponent {
        static template = 'OrderlineNoteButton';
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
                startingValue: this.selectedOrderline.get_note(),
                title: this.env._t('Add Note'),
            });

            if (confirmed) {
                this.selectedOrderline.set_note(inputNote);
            }
        }
    }

    ProductScreen.addControlButton({
        component: OrderlineNoteButton,
        condition: function() {
            return this.env.pos.config.module_pos_restaurant;
        },
    });

    Registry.add('OrderlineNoteButton', OrderlineNoteButton);

    return { OrderlineNoteButton };
});
