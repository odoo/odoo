odoo.define('point_of_sale.PSNumpadInputButton', function(require) {
    'use strict';

    const { PosComponent } = require('point_of_sale.PosComponent');

    class PSNumpadInputButton extends PosComponent {
        get _class() {
            return this.props.changeClassTo || 'input-button number-char';
        }
    }

    return { PSNumpadInputButton };
});
