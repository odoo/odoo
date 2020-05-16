odoo.define('point_of_sale.HomeCategoryBreadcrumb', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class HomeCategoryBreadcrumb extends PosComponent {}
    HomeCategoryBreadcrumb.template = 'HomeCategoryBreadcrumb';

    Registries.Component.add(HomeCategoryBreadcrumb);

    return HomeCategoryBreadcrumb;
});
