odoo.define('point_of_sale.PosContext', function (require) {
    'use strict';
    const { reactive } = owl;

    // Create global context objects
    // e.g. component.env.device = new Context({ isMobile: false });
    return {
        orderManagement: reactive({ searchString: '', selectedOrder: null }),
    };
});
