odoo.define('pos_restaurant.SplitOrderline', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const { sum } = require('point_of_sale.utils');
    const { format } = require('web.field_utils');
    const { useListener } = require('web.custom_hooks');

    class SplitOrderline extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('click', this.onClick);
        }
        onClick() {
            this.trigger('click-line', this.props.line);
        }
        getDisplayPrice(...allOrderlinePrices) {
            const [first, ...rest] = allOrderlinePrices;
            const summary = { ...first };
            for (const prices of rest) {
                for (const key in prices) {
                    summary[key] += prices[key];
                }
            }
            return this.env.model.getOrderlineDisplayPrice(summary);
        }
        getQuantityStrOfLines(...orderlines) {
            const totalQty = sum(orderlines, (line) => line.qty);
            const product = this.env.model.getRecord('product.product', orderlines[0].product_id);
            const unit = this.env.model.getRecord('uom.uom', product.uom_id);
            if (unit) {
                if (unit.rounding) {
                    const decimals = this.env.model.getDecimalPrecision('Product Unit of Measure').digits;
                    return format.float(totalQty, { digits: [false, decimals] });
                } else {
                    return totalQty.toFixed(0);
                }
            } else {
                return '' + totalQty;
            }
        }
    }
    SplitOrderline.template = 'pos_restaurant.SplitOrderline';

    return SplitOrderline;
});
