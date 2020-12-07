odoo.define('pos_restaurant.ProductScreen', function (require) {
    'use strict';

    const ProductScreen = require('point_of_sale.ProductScreen');
    const OrderlineNoteButton = require('pos_restaurant.OrderlineNoteButton');
    const TableGuestsButton = require('pos_restaurant.TableGuestsButton');
    const TransferOrderButton = require('pos_restaurant.TransferOrderButton');
    const SplitBillButton = require('pos_restaurant.SplitBillButton');
    const PrintBillButton = require('pos_restaurant.PrintBillButton');
    const SubmitOrderButton = require('pos_restaurant.SubmitOrderButton');
    const { patch } = require('web.utils');


    patch(ProductScreen, 'pos_restaurant', {
        components: {
            ...ProductScreen.components,
            OrderlineNoteButton,
            TableGuestsButton,
            TransferOrderButton,
            SplitBillButton,
            PrintBillButton,
            SubmitOrderButton,
        },
    });

    patch(ProductScreen.prototype, 'pos_restaurant', {
        getOrderlineAdditionalClasses(orderline) {
            return Object.assign(this._super(...arguments), {
                dirty: orderline.mp_dirty,
                skip: orderline.mp_skip,
            });
        },
    });

    return ProductScreen;
});
