odoo.define('point_of_sale.TableGuestsButton', function(require) {
    'use strict';

    const { PosComponent } = require('point_of_sale.PosComponent');
    const { ProductScreen } = require('point_of_sale.ProductScreen');
    const { useListener } = require('web.custom_hooks');
    const Registry = require('point_of_sale.ComponentsRegistry');

    class TableGuestsButton extends PosComponent {
        static template = 'TableGuestsButton';
        constructor() {
            super(...arguments);
            useListener('click', this.onClick);
        }
        get currentOrder() {
            return this.env.pos.get_order();
        }
        get nGuests() {
            return this.currentOrder.get_customer_count();
        }
        async onClick() {
            const { confirmed, payload: inputNumber } = await this.showPopup('NumberPopup', {
                startingValue: this.nGuests,
                cheap: true,
                title: this.env._t('Guests ?'),
            });

            if (confirmed) {
                this.env.pos.get_order().set_customer_count(parseInt(inputNumber, 10) || 1);
            }
        }
    }

    ProductScreen.addControlButton({
        component: TableGuestsButton,
        condition: function() {
            return true;
        },
    });

    Registry.add('TableGuestsButton', TableGuestsButton);

    return { TableGuestsButton };
});
