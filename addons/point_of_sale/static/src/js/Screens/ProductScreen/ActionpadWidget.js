odoo.define('point_of_sale.ActionpadWidget', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    /**
     * @props client
     * @emits click-customer
     * @emits click-pay
     */
    class ActionpadWidget extends PosComponent {
        get isLongName() {
            return this.props.client && this.props.client.name.length > 10;
        }
    }
    ActionpadWidget.template = 'ActionpadWidget';
    ActionpadWidget.defaultProps = {
        isActionButtonHighlighted: false,
    }

    Registries.Component.add(ActionpadWidget);

    return ActionpadWidget;
});
