odoo.define('point_of_sale.PosContext', function (require) {
    'use strict';

    const { Context } = owl;

    // Create global context objects
    // e.g. component.env.device = new Context({ isMobile: false });
    return {
        orderManagement: new Context({ searchString: '', selectedOrder: null }),
        chrome: new Context({ showOrderSelector: true }),
    };
});
