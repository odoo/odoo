odoo.define('pos_restaurant.TableGuestsButton', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const { useListener } = require('web.custom_hooks');
    const Registries = require('point_of_sale.Registries');

    class TableGuestsButton extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('click', this.onClick);
        }
        get currentOrder() {
            return this.env.pos.get_order();
        }
        get nGuests() {
            return this.currentOrder ? this.currentOrder.get_customer_count() : 0;
        }
        async onClick() {
            const { confirmed, payload: inputNumber } = await this.showPopup('NumberPopup', {
                startingValue: this.nGuests,
                cheap: true,
                title: this.env._t('Guests ?'),
                isInputSelected: true
            });

            if (confirmed) {
                const guestCount = parseInt(inputNumber, 10) || 1;
                // Set the maximum number possible for an integer
                const max_capacity = 2**31 - 1;
                if (guestCount > max_capacity) {
                    await this.showPopup('ErrorPopup', {
                        title: this.env._t('Blocked action'),
                        body: _.str.sprintf(
                            this.env._t('You cannot put a number that exceeds %s '),
                            max_capacity,
                        ),
                    });
                    return;
                }
                this.env.pos.get_order().set_customer_count(guestCount);
            }
        }
    }
    TableGuestsButton.template = 'TableGuestsButton';

    ProductScreen.addControlButton({
        component: TableGuestsButton,
        condition: function() {
            return this.env.pos.config.module_pos_restaurant;
        },
    });

    Registries.Component.add(TableGuestsButton);

    return TableGuestsButton;
});
