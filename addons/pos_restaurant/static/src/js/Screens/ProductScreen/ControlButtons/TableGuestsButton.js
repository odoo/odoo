odoo.define('pos_restaurant.TableGuestsButton', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const { useListener } = require("@web/core/utils/hooks");
    const Registries = require('point_of_sale.Registries');

    class TableGuestsButton extends PosComponent {
        setup() {
            super.setup();
            useListener('click', this.onClick);
        }
        get currentOrder() {
            return this.env.pos.get_order();
        }
        get nGuests() {
            return this.currentOrder ? this.currentOrder.getCustomerCount() : 0;
        }
        async onClick() {
            const { confirmed, payload: inputNumber } = await this.showPopup('NumberPopup', {
                startingValue: this.nGuests,
                cheap: true,
                title: this.env._t('Guests ?'),
                isInputSelected: true
            });

            if (confirmed) {
                this.env.pos.get_order().setCustomerCount(parseInt(inputNumber, 10) || 1);
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
