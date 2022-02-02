odoo.define('pos_restaurant.SubmitOrderButton', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const { useListener } = require('web.custom_hooks');
    const Registries = require('point_of_sale.Registries');

    const { onWillUnmount } = owl;

    /**
     * IMPROVEMENT: Perhaps this class is quite complicated for its worth.
     * This is because it needs to listen to changes to the current order.
     * Also, the current order changes when the selectedOrder in pos is changed.
     * After setting new current order, we update the listeners.
     */
    class SubmitOrderButton extends PosComponent {
        setup() {
            useListener('click', this.onClick);
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
        get currentOrder() {
            return this.env.pos.get_order();
        }
        get addedClasses() {
            if (!this.currentOrder) return {};
            const changes = this.currentOrder.hasChangesToPrint();
            const skipped = changes ? false : this.currentOrder.hasSkippedChanges();
            return {
                highlight: changes,
                altlight: skipped,
            };
        }
    }
    SubmitOrderButton.template = 'SubmitOrderButton';

    ProductScreen.addControlButton({
        component: SubmitOrderButton,
        condition: function() {
            return this.env.pos.config.module_pos_restaurant && this.env.pos.unwatched.printers.length;
        },
    });

    Registries.Component.add(SubmitOrderButton);

    return SubmitOrderButton;
});
