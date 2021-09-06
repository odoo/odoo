    odoo.define('point_of_sale.GiftVoucherLine', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class GiftVoucherLine extends PosComponent {
        get highlight() {
            return this.props.gift_card !== this.props.selectedVoucher ? '' : 'highlight';
        }
    }
    GiftVoucherLine.template = 'GiftVoucherLine';

    Registries.Component.add(GiftVoucherLine);

    return GiftVoucherLine;
});
