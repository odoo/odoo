odoo.define('point_of_sale.PSNumpadInputButton', function(require) {
    'use strict';

    const { PosComponent } = require('point_of_sale.PosComponent');
    const Registry = require('point_of_sale.ComponentsRegistry');

    class PSNumpadInputButton extends PosComponent {
        static template = 'PSNumpadInputButton';
        get _class() {
            return this.props.changeClassTo || 'input-button number-char';
        }
    }

    Registry.add('PSNumpadInputButton', PSNumpadInputButton);

    return { PSNumpadInputButton };
});
