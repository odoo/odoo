odoo.define('pos_restaurant.TableGuestsButton', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const { useListener } = require('web.custom_hooks');

    class TableGuestsButton extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('click', this.onClick);
        }
        get nGuests() {
            return this.props.activeOrder.customer_count || 0;
        }
        async onClick() {
            const [confirmed, inputNumber] = await this.env.ui.askUser('NumberPopup', {
                startingValue: this.nGuests,
                cheap: true,
                title: this.env._t('Guests ?'),
                isInputSelected: true
            });

            if (confirmed) {
                await this.env.model.actionHandler({
                    name: 'actionSetCustomerCount',
                    args: [this.props.activeOrder, parseInt(inputNumber, 10) || 1],
                });
            }
        }
    }
    TableGuestsButton.template = 'pos_restaurant.TableGuestsButton';

    return TableGuestsButton;
});
