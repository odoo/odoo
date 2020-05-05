odoo.define('point_of_sale.NumpadWidget', function(require) {
    'use strict';

    const { useState } = owl;
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    /**
     * IMPROVEMENT: Whenever new-orderline-selected is triggered,
     * numpad mode should be set to 'quantity'.
     */
    class NumpadWidget extends PosComponent {
        constructor() {
            super(...arguments);
            this.state = useState({ mode: 'quantity' });
        }
        mounted() {
            this.env.pos.on('change:cashier', () => {
                if (!this.hasPriceControlRights && this.state.mode === 'price') {
                    this.state.mode = 'quantity';
                }
            });
        }
        willUnmount() {
            this.env.pos.on('change:cashier', null, this);
        }
        get hasPriceControlRights() {
            const cashier = this.env.pos.get('cashier') || this.env.pos.get_cashier();
            return !this.env.pos.config.restrict_price_control || cashier.role == 'manager';
        }
        changeMode(mode) {
            if (!this.hasPriceControlRights && mode === 'price') {
                return;
            }
            this.state.mode = mode;
            this.trigger('set-numpad-mode', { mode });
        }
        sendInput(key) {
            this.trigger('numpad-click-input', { key });
        }
    }
    NumpadWidget.template = 'NumpadWidget';

    Registries.Component.add(NumpadWidget);

    return NumpadWidget;
});
