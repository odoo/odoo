odoo.define('pos_restaurant.OrderlineNoteButton', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const { useListener } = require('web.custom_hooks');

    class OrderlineNoteButton extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('click', this.onClick);
        }
        async onClick() {
            const activeOrderline = this.env.model.getActiveOrderline(this.props.activeOrder);
            if (!activeOrderline) return;
            const [confirmed, inputNote] = await this.env.ui.askUser('TextAreaPopup', {
                startingValue: activeOrderline.note || '',
                title: this.env._t('Add Note'),
            });
            if (confirmed) {
                await this.env.model.actionHandler({ name: 'actionUpdateOrderline', args: [activeOrderline, { note: inputNote }] });
            }
        }
    }
    OrderlineNoteButton.template = 'pos_restaurant.OrderlineNoteButton';

    return OrderlineNoteButton;
});
