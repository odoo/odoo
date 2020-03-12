odoo.define('pos_hr.chrome', function(require) {
    'use strict';

    const { Chrome } = require('point_of_sale.chrome');
    const Registry = require('point_of_sale.ComponentsRegistry');

    const PosHrChrome = Chrome =>
        class extends Chrome {
            async start() {
                await super.start();
                this.env.pos.on('change:client', this.render, this);
                if (this.env.pos.config.module_pos_hr) this.showTempScreen('LoginScreen');
            }
            get headerButtonIsShown() {
                return this.env.pos.get('cashier').role == 'manager';
            }
        };

    Registry.extend(Chrome.name, PosHrChrome);
});
