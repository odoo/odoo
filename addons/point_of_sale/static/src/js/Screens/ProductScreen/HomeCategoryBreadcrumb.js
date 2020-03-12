odoo.define('point_of_sale.HomeCategoryBreadcrumb', function(require) {
    'use strict';

    const { PosComponent } = require('point_of_sale.PosComponent');
    const Registry = require('point_of_sale.ComponentsRegistry');

    class HomeCategoryBreadcrumb extends PosComponent {
        static template = 'HomeCategoryBreadcrumb';
    }

    Registry.add('HomeCategoryBreadcrumb', HomeCategoryBreadcrumb);

    return { HomeCategoryBreadcrumb };
});
