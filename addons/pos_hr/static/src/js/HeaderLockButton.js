odoo.define('point_of_sale.HeaderLockButton', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    const { useState } = owl;

    class HeaderLockButton extends PosComponent {
        setup() {
            super.setup();
            this.state = useState({ isUnlockIcon: true, title: 'Unlocked' });
        }
        async showLoginScreen() {
            this.env.pos.reset_cashier();
            await this.showTempScreen('LoginScreen');
        }
        onMouseOver(isMouseOver) {
            this.state.isUnlockIcon = !isMouseOver;
            this.state.title = isMouseOver ? 'Lock' : 'Unlocked';
        }
    }
    HeaderLockButton.template = "HeaderLockButton";

    Registries.Component.add(HeaderLockButton);

    return HeaderLockButton;
});
