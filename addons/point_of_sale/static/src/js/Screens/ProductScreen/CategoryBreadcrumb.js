odoo.define('point_of_sale.CategoryBreadcrumb', function(require) {
    'use strict';

    const { PosComponent } = require('point_of_sale.PosComponent');
    const Registry = require('point_of_sale.ComponentsRegistry');

    class CategoryBreadcrumb extends PosComponent {
        static template = 'CategoryBreadcrumb';
    }

    Registry.add('CategoryBreadcrumb', CategoryBreadcrumb);

    return { CategoryBreadcrumb };
});
