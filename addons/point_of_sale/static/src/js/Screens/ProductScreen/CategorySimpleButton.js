odoo.define('point_of_sale.CategorySimpleButton', function(require) {
    'use strict';

    const { PosComponent } = require('point_of_sale.PosComponent');

    class CategorySimpleButton extends PosComponent {
        static template = 'CategorySimpleButton';
    }

    return { CategorySimpleButton };
});
