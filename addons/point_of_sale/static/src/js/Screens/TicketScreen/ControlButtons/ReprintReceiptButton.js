odoo.define('point_of_sale.ReprintReceiptButton', function (require) {
    'use strict';

    const { useListener } = require("@web/core/utils/hooks");
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class ReprintReceiptButton extends PosComponent {
        setup() {
            super.setup();
            useListener('click', this._onClick);
        }
        async _onClick() {
            if (!this.props.order) return;
            this.showScreen('ReprintReceiptScreen', { order: this.props.order });
        }
    }
    ReprintReceiptButton.template = 'ReprintReceiptButton';
    Registries.Component.add(ReprintReceiptButton);

    return ReprintReceiptButton;
});
