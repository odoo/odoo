odoo.define('point_of_sale.HeaderButton', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    // Previously HeaderButtonWidget
    // This is the close session button
    class HeaderButton extends PosComponent {
        async onClick() {
            const info = await this.env.pos.getClosePosInfo();
            this.showPopup('ClosePosPopup', { info: info });
        }
    }
    HeaderButton.template = 'HeaderButton';

    Registries.Component.add(HeaderButton);

    return HeaderButton;
});
