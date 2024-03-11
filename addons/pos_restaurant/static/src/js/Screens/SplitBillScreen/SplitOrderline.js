odoo.define('pos_restaurant.SplitOrderline', function(require) {
    'use strict';

    const { useListener } = require("@web/core/utils/hooks");
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class SplitOrderline extends PosComponent {
        setup() {
            super.setup();
            useListener('click', this.onClick);
        }
        get isSelected() {
            return this.props.split.quantity !== 0;
        }
        onClick() {
            this.trigger('click-line', this.props.line);
        }
    }
    SplitOrderline.template = 'SplitOrderline';

    Registries.Component.add(SplitOrderline);

    return SplitOrderline;
});
