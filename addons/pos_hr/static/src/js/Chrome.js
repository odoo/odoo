odoo.define('pos_hr.chrome', function(require) {
    'use strict';

    const { Chrome } = require('point_of_sale.chrome');
    const { patch } = require('web.utils');

    const unpatchChrome = patch(Chrome, 'pos_hr', {
        start: async function() {
            await this._super();
            this.env.pos.on('change:client', this.render, this);
            if (this.env.pos.config.module_pos_hr) this.showTempScreen('LoginScreen');
        },
        get headerButtonIsShown() {
            return this.env.pos.get('cashier').role == 'manager';
        },
    });

    return { unpatchChrome };
});
