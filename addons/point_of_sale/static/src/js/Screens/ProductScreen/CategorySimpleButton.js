odoo.define('point_of_sale.CategorySimpleButton', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class CategorySimpleButton extends PosComponent {}
    CategorySimpleButton.template = 'CategorySimpleButton';

    Registries.Component.add(CategorySimpleButton);

    return CategorySimpleButton;
});
