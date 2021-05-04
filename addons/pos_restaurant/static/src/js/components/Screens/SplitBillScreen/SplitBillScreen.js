odoo.define('pos_restaurant.SplitBillScreen', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const SplitOrderline = require('pos_restaurant.SplitOrderline');
    const { useListener } = require('web.custom_hooks');
    const { useState } = owl.hooks;
    const { sum } = require('point_of_sale.utils');

    class SplitBillScreen extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('click-line', this._onClickLine);
            const [splitlines, groupedOrderlines] = this._initSplitLines(this.props.activeOrder);
            this.splitlines = useState(splitlines);
            this.groupedOrderlines = groupedOrderlines;
        }
        async onProceed() {
            if (this._hasEmptySplit()) {
                this.env.ui.showNotification(this.env._t('Nothing to split.'));
            } else {
                await this.env.model.actionHandler({
                    name: 'actionSplitOrder',
                    args: [this.props.activeOrder, this.splitlines, this.props.disallow],
                });
            }
        }
        _onClickLine(event) {
            this._splitQuantity(event.detail);
        }
        /**
         * @param {models.Order} order
         * @returns {Object<{ quantity: number }>} splitlines
         */
        _initSplitLines(order) {
            const splitlines = {};
            const groupedOrderlines = this.env.model.getGroupedOrderlines(this.env.model.getOrderlines(order));
            for (const lineId in groupedOrderlines) {
                const line = this.env.model.getRecord('pos.order.line', lineId);
                const mergeableLines = groupedOrderlines[lineId].map((id) =>
                    this.env.model.getRecord('pos.order.line', id)
                );
                splitlines[line.id] = {
                    product: line.product_id,
                    quantity: 0,
                    maxQuantity: sum([line, ...mergeableLines], (line) => line.qty),
                };
            }
            return [splitlines, groupedOrderlines];
        }
        _splitQuantity(line) {
            const split = this.splitlines[line.id];
            const unit = this.env.model.getOrderlineUnit(line);
            if (this.env.model.floatLT(split.quantity, split.maxQuantity)) {
                split.quantity += unit.is_pos_groupable ? 1 : unit.rounding;
                if (this.env.model.floatGT(split.quantity, split.maxQuantity)) {
                    split.quantity = split.maxQuantity;
                }
            } else {
                split.quantity = 0;
            }
        }
        _hasEmptySplit() {
            for (const lineId in this.splitlines) {
                const split = this.splitlines[lineId];
                if (!this.env.model.floatEQ(split.quantity, 0, 5)) {
                    return false;
                }
            }
            return true;
        }
        getGroupedLinesToShow() {
            const result = [];
            for (const lineId in this.groupedOrderlines) {
                const referenceLine = this.env.model.getRecord('pos.order.line', lineId);
                const otherLines = this.groupedOrderlines[lineId].map((id) =>
                    this.env.model.getRecord('pos.order.line', id)
                );
                if (
                    this.env.model.floatGT(
                        sum([referenceLine, ...otherLines], (line) => line.qty),
                        0
                    )
                ) {
                    result.push([lineId, referenceLine, otherLines]);
                }
            }
            return result;
        }
    }
    SplitBillScreen.components = { SplitOrderline };
    SplitBillScreen.template = 'pos_restaurant.SplitBillScreen';

    return SplitBillScreen;
});
