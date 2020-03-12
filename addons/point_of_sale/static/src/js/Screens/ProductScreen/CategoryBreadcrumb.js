odoo.define('point_of_sale.CategoryBreadcrumb', function(require) {
    'use strict';

    const { PosComponent } = require('point_of_sale.PosComponent');

    class CategoryBreadcrumb extends PosComponent {
        static template = 'CategoryBreadcrumb';
    }

    return { CategoryBreadcrumb };
});
