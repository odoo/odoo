odoo.define('point_of_sale.SplitBillScreen', function(require) {
    'use strict';

    const { PosComponent } = require('point_of_sale.PosComponent');
    const { useState } = owl.hooks;
    const { useListener } = require('web.custom_hooks');
    const models = require('point_of_sale.models');
    const Registry = require('point_of_sale.ComponentsRegistry');

    class SplitBillScreen extends PosComponent {
        static template = 'SplitBillScreen';
        constructor() {
            super(...arguments);
            useListener('click-line', this.onClickLine);
            this.splitlines = useState(this._initSplitLines(this.env.pos.get_order()));
            this.newOrderLines = {};
            this.newOrder = new models.Order(
                {},
                {
                    pos: this.env.pos,
                    temporary: true,
                }
            );
            this._isFinal = false;
        }
        mounted() {
            this.env.pos.on('change:selectedOrder', this._resetState, this);
            this.newOrder.on('change', this.render, this);
        }
        willUnmount() {
            this.env.pos.off('change:selectedOrder', null, this);
            this.newOrder.off('change', null, this);
        }
        get currentOrder() {
            return this.env.pos.get_order();
        }
        get orderlines() {
            return this.currentOrder.get_orderlines();
        }
        onClickLine(event) {
            const line = event.detail;
            this._splitQuantity(line);
            this._updateNewOrder(line);
        }
        back() {
            this.showScreen('ProductScreen');
        }
        proceed() {
            if (_.isEmpty(this.splitlines))
                // Splitlines is empty
                return;

            this._isFinal = true;
            delete this.newOrder.temporary;

            if (this._isFullPayOrder()) {
                this.showScreen('PaymentScreen');
            } else {
                this._setQuantityOnCurrentOrder();

                this.newOrder.set_screen_data('screen', { name: 'PaymentScreen' });

                // for the kitchen printer we assume that everything
                // has already been sent to the kitchen before splitting
                // the bill. So we save all changes both for the old
                // order and for the new one. This is not entirely correct
                // but avoids flooding the kitchen with unnecessary orders.
                // Not sure what to do in this case.

                if (this.newOrder.saveChanges) {
                    this.currentOrder.saveChanges();
                    this.newOrder.saveChanges();
                }

                this.newOrder.set_customer_count(1);
                this.currentOrder.set_customer_count(this.currentOrder.get_customer_count() - 1);
                this.currentOrder.set_screen_data('screen', { name: 'ProductScreen' });

                this.env.pos.get('orders').add(this.newOrder);
                this.env.pos.set('selectedOrder', this.newOrder);
            }
        }
        /**
         * @param {models.Order} order
         * @returns {Object<{ quantity: number }>} splitlines
         */
        _initSplitLines(order) {
            const splitlines = {};
            for (let line of order.get_orderlines()) {
                splitlines[line.id] = { quantity: 0 };
            }
            return splitlines;
        }
        _splitQuantity(line) {
            const split = this.splitlines[line.id];
            if (!line.get_unit().is_pos_groupable) {
                if (split.quantity !== line.get_quantity()) {
                    split.quantity = line.get_quantity();
                } else {
                    split.quantity = 0;
                }
            } else {
                if (split.quantity < line.get_quantity()) {
                    split.quantity += line.get_unit().is_pos_groupable
                        ? 1
                        : line.get_unit().rounding;
                    if (split.quantity > line.get_quantity()) {
                        split.quantity = line.get_quantity();
                    }
                } else {
                    split.quantity = 0;
                }
            }
        }
        _updateNewOrder(line) {
            const split = this.splitlines[line.id];
            let orderline = this.newOrderLines[line.id];
            if (split.quantity) {
                if (!orderline) {
                    orderline = line.clone();
                    this.newOrder.add_orderline(orderline);
                    this.newOrderLines[line.id] = orderline;
                }
                orderline.set_quantity(split.quantity, 'do not recompute unit price');
            } else if (orderline) {
                this.newOrder.remove_orderline(orderline);
                this.newOrderLines[line.id] = null;
            }
        }
        _isFullPayOrder() {
            return _.every(this.currentOrder.get_orderlines(), orderLine => {
                var split = this.splitlines[orderLine.id];
                return split && split.quantity === orderLine.get_quantity();
            });
        }
        _setQuantityOnCurrentOrder() {
            for (var id in this.splitlines) {
                var split = this.splitlines[id];
                var line = this.currentOrder.get_orderline(parseInt(id));
                line.set_quantity(
                    line.get_quantity() - split.quantity,
                    'do not recompute unit price'
                );
                if (Math.abs(line.get_quantity()) < 0.00001) {
                    this.currentOrder.remove_orderline(line);
                }
                delete this.splitlines[id];
            }
        }
        _resetState() {
            if (this._isFinal) return;

            for (let id in this.splitlines) {
                delete this.splitlines[id];
            }
            for (let line of this.currentOrder.get_orderlines()) {
                this.splitlines[line.id] = { quantity: 0 };
            }
            this.newOrder.orderlines.reset();
        }
    }

    Registry.add('SplitBillScreen', SplitBillScreen);

    return { SplitBillScreen };
});
