odoo.define('pos_hr.HeaderLockButton', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const { useState } = owl;

    class HeaderLockButton extends PosComponent {
        constructor() {
            super(...arguments);
            this.state = useState({ isUnlockIcon: true, title: 'Unlocked' });
        }
        onMouseOver(isMouseOver) {
            this.state.isUnlockIcon = !isMouseOver;
            this.state.title = isMouseOver ? 'Lock' : 'Unlocked';
        }
    }
    HeaderLockButton.template = 'pos_hr.HeaderLockButton';

    return HeaderLockButton;
});
