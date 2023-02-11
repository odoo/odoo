odoo.define('pos_restaurant.SubmitOrderButton', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const { useListener } = require('web.custom_hooks');
    const Registries = require('point_of_sale.Registries');

    /**
     * IMPROVEMENT: Perhaps this class is quite complicated for its worth.
     * This is because it needs to listen to changes to the current order.
     * Also, the current order changes when the selectedOrder in pos is changed.
     * After setting new current order, we update the listeners.
     */
    class SubmitOrderButton extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('click', this.onClick);
            this._currentOrder = this.env.pos.get_order();
            this._currentOrder.orderlines.on('change', this.render, this);
            this.env.pos.on('change:selectedOrder', this._updateCurrentOrder, this);
        }
        willUnmount() {
            this._currentOrder.orderlines.off('change', null, this);
            this.env.pos.off('change:selectedOrder', null, this);
        }
        async onClick() {
            const order = this.env.pos.get_order();
            if (order.hasChangesToPrint()) {
                const isPrintSuccessful = await order.printChanges();
                if (isPrintSuccessful) {
                    order.saveChanges();
                } else {
                    await this.showPopup('ErrorPopup', {
                        title: this.env._t('Printing failed'),
                        body: this.env._t('Failed in printing the changes in the order'),
                    });
                }
            }
        }
        get addedClasses() {
            if (!this._currentOrder) return {};
            const changes = this._currentOrder.hasChangesToPrint();
            const skipped = changes ? false : this._currentOrder.hasSkippedChanges();
            return {
                highlight: changes,
                altlight: skipped,
            };
        }
        _updateCurrentOrder(pos, newSelectedOrder) {
            this._currentOrder.orderlines.off('change', null, this);
            if (newSelectedOrder) {
                this._currentOrder = newSelectedOrder;
                this._currentOrder.orderlines.on('change', this.render, this);
            }
        }
    }
    SubmitOrderButton.template = 'SubmitOrderButton';

    ProductScreen.addControlButton({
        component: SubmitOrderButton,
        condition: function() {
            return this.env.pos.printers.length;
        },
    });

    Registries.Component.add(SubmitOrderButton);

    return SubmitOrderButton;
});
