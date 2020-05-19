odoo.define('pos_hr.chrome', function (require) {
    'use strict';

    const Chrome = require('point_of_sale.Chrome');
    const Registries = require('point_of_sale.Registries');

    const PosHrChrome = (Chrome) =>
        class extends Chrome {
            async start() {
                await super.start();
                if (this.env.pos.config.module_pos_hr) {
                    this.env.pos.on('change:cashier', this.render, this);
                }
            }
            get headerButtonIsShown() {
                return this.env.pos.config.module_pos_hr
                    ? this.env.pos.get('cashier').role == 'manager'
                    : true;
            }
        };

    Registries.Component.extend(Chrome, PosHrChrome);

    return Chrome;
});
