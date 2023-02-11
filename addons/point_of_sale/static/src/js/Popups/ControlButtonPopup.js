odoo.define('point_of_sale.ControlButtonPopup', function(require) {
    'use strict';

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const { _lt } = require('@web/core/l10n/translation');

    class ControlButtonPopup extends AbstractAwaitablePopup {
        /**
         * @param {Object} props
         * @param {string} props.startingValue
         */
        constructor() {
            super(...arguments);
            this.controlButtons = this.props.controlButtons;
        }
    }
    ControlButtonPopup.template = 'ControlButtonPopup';
    ControlButtonPopup.defaultProps = {
        cancelText: _lt('Back'),
        controlButtons: []
    };

    Registries.Component.add(ControlButtonPopup);

    return ControlButtonPopup;
});
