odoo.define('pos_restaurant.PointOfSaleUI', function (require) {
    'use strict';

    const PointOfSaleUI = require('point_of_sale.PointOfSaleUI');
    const FloorScreen = require('pos_restaurant.FloorScreen');
    const TipScreen = require('pos_restaurant.TipScreen');
    const SplitBillScreen = require('pos_restaurant.SplitBillScreen');
    const BillScreen = require('pos_restaurant.BillScreen');
    const BackToFloorButton = require('pos_restaurant.BackToFloorButton');
    const { patch } = require('web.utils');

    patch(PointOfSaleUI.prototype, 'pos_restaurant', {
        setup() {
            this._super();
            // We save the orderIdsToRemove before the app is reloaded or closed.
            owl.hooks.useExternalListener(window, 'unload', this._saveOrderIdsToRemove);
        },
        _saveOrderIdsToRemove() {
            this.env.model.storage.setItem(
                `${this.env.model.getStorageKeyPrefix('others')}/orderIdsToRemove`,
                JSON.stringify([...this.env.model.orderIdsToRemove])
            );
        }
    })

    patch(PointOfSaleUI, 'pos_restaurant', {
        components: {
            ...PointOfSaleUI.components,
            FloorScreen,
            SplitBillScreen,
            BillScreen,
            BackToFloorButton,
            TipScreen,
        },
    });

    return PointOfSaleUI;
});
