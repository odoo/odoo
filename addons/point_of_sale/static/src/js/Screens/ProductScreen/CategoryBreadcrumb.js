odoo.define('point_of_sale.CategoryBreadcrumb', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class CategoryBreadcrumb extends PosComponent {}
    CategoryBreadcrumb.template = 'CategoryBreadcrumb';

    Registries.Component.add(CategoryBreadcrumb);

    return CategoryBreadcrumb;
});
