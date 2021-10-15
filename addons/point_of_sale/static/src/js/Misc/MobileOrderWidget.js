odoo.define('point_of_sale.MobileOrderWidget', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class MobileOrderWidget extends PosComponent {
        get order() {
            return this.env.pos.get_order();
        }
        get total() {
            const _total = this.order ? this.order.get_total_with_tax() : 0;
            return this.env.pos.format_currency(_total);
        }
        get items_number() {
            return this.order ? this.order.orderlines.reduce((items_number,line) => items_number + line.quantity, 0) : 0;
        }
    }

    MobileOrderWidget.template = 'MobileOrderWidget';

    Registries.Component.add(MobileOrderWidget);

    return MobileOrderWidget;
});
