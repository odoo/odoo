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
                return !this.env.pos.config.module_pos_hr || this.env.pos.get('cashier').role == 'manager' || this.env.pos.get_cashier().user_id[0] === this.env.pos.user.id;
            }
            showCashMoveButton() {
                return super.showCashMoveButton() && (this.env.pos.get('cashier').role == 'manager' || this.env.pos.get_cashier().user_id);
            }
            shouldShowCashControl() {
                return super.shouldShowCashControl() && this.env.pos.hasLoggedIn;
            }
            _shouldResetIdleTimer() {
                return super._shouldResetIdleTimer() && this.tempScreen.name !== 'LoginScreen';
            }
        };

    Registries.Component.extend(Chrome, PosHrChrome);

    return Chrome;
});
