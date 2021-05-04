odoo.define('pos_restaurant.SubmitOrderButton', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const { useListener } = require('web.custom_hooks');
    class SubmitOrderButton extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('click', this.onClick);
        }
        async onClick() {
            await this.env.model.actionHandler({ name: 'actionPrintResumeChanges', args: [this.props.activeOrder] });
        }
        get addedClasses() {
            const order = this.props.activeOrder;
            const changes = this.env.model.hasResumeChangesToPrint(order);
            const skipped = changes ? false : this.env.model.hasSkippedResumeChanges(order);
            return {
                highlight: changes,
                altlight: skipped,
            };
        }
    }
    SubmitOrderButton.template = 'pos_restaurant.SubmitOrderButton';

    return SubmitOrderButton;
});
