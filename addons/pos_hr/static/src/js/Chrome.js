odoo.define('pos_hr.chrome', function (require) {
    'use strict';

    const Chrome = require('point_of_sale.Chrome');
    const Registries = require('point_of_sale.Registries');

    const PosHrChrome = (Chrome) =>
        class extends Chrome {
            async start() {
                await super.start();
                this.env.pos.on('change:cashier', this.render, this);
                if (this.env.pos.config.module_pos_hr) this.showTempScreen('LoginScreen');
            }
            get headerButtonIsShown() {
                return !this.env.pos.config.module_pos_hr || this.env.pos.get('cashier').role == 'manager';
            }
        };

    Registries.Component.extend(Chrome, PosHrChrome);

    return Chrome;
});
