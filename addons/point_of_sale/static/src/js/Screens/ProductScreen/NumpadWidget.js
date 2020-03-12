odoo.define('point_of_sale.NumpadWidget', function(require) {
    'use strict';

    const { useState } = owl;
    const { PosComponent } = require('point_of_sale.PosComponent');

    class NumpadWidget extends PosComponent {
        static template = 'NumpadWidget';
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
        get hasPriceControlRights() {
            const cashier = this.env.pos.get('cashier') || this.env.pos.get_cashier();
            return !this.env.pos.config.restrict_price_control || cashier.role == 'manager';
        }
        changeMode(mode) {
            if (!this.hasPriceControlRights && this.state.mode === 'price') {
                return;
            }
            this.state.mode = mode;
            this.trigger('set-numpad-mode', { mode });
        }
        sendInput(key) {
            this.trigger('numpad-click-input', { key });
        }
    }

    return { NumpadWidget };
});
