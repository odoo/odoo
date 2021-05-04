odoo.define('pos_coupon.ResetProgramsButton', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const { useListener } = require('web.custom_hooks');

    class ResetProgramsButton extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('click', this.onClick);
        }
        async onClick() {
            await this.env.model.actionHandler({ name: 'actionResetPrograms', args: [this.props.activeOrder] });
        }
    }
    ResetProgramsButton.template = 'pos_coupon.ResetProgramsButton';

    return ResetProgramsButton;
});
