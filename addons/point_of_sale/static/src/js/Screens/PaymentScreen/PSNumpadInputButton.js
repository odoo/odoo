odoo.define('point_of_sale.PSNumpadInputButton', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class PSNumpadInputButton extends PosComponent {
        get _class() {
            return this.props.changeClassTo || 'input-button number-char';
        }
    }
    PSNumpadInputButton.template = 'PSNumpadInputButton';

    Registries.Component.add(PSNumpadInputButton);

    return PSNumpadInputButton;
});
