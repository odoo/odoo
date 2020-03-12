odoo.define('point_of_sale.CategorySimpleButton', function(require) {
    'use strict';

    const { PosComponent } = require('point_of_sale.PosComponent');
    const Registry = require('point_of_sale.ComponentsRegistry');

    class CategorySimpleButton extends PosComponent {
        static template = 'CategorySimpleButton';
    }

    Registry.add('CategorySimpleButton', CategorySimpleButton);

    return { CategorySimpleButton };
});
