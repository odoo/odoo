odoo.define('pos_restaurant.OrderlineNoteButton', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const { useListener } = require('web.custom_hooks');
    const Registries = require('point_of_sale.Registries');

    class OrderlineNoteButton extends PosComponent {
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
                title: this.env._t('Add Internal Note'),
            });

            if (confirmed) {
                this.selectedOrderline.set_note(inputNote);
            }
        }
    }
    OrderlineNoteButton.template = 'OrderlineNoteButton';
    Registries.Component.add(OrderlineNoteButton);

    return OrderlineNoteButton;
});
