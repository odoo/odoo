odoo.define('point_of_sale.HeaderLockButton', function(require) {
    'use strict';

    const { Chrome } = require('point_of_sale.chrome');
    const { PosComponent, addComponents } = require('point_of_sale.PosComponent');
    const { useState } = owl;

    class HeaderLockButton extends PosComponent {
        state = useState({ isUnlockIcon: true, title: 'Unlocked' });
        async showLoginScreen() {
            await this.showTempScreen('LoginScreen');
        }
        onMouseOver(isMouseOver) {
            this.state.isUnlockIcon = !isMouseOver;
            this.state.title = isMouseOver ? 'Lock' : 'Unlocked';
        }
    }

    addComponents(Chrome, [HeaderLockButton]);

    return { HeaderLockButton };
});
