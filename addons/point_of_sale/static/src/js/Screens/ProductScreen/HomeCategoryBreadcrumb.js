odoo.define('point_of_sale.HomeCategoryBreadcrumb', function(require) {
    'use strict';

    const { PosComponent } = require('point_of_sale.PosComponent');

    class HomeCategoryBreadcrumb extends PosComponent {
        static template = 'HomeCategoryBreadcrumb';
    }

    return { HomeCategoryBreadcrumb };
});
