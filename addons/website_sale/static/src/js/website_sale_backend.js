odoo.define('website_sale.backend', function (require) {
"use strict";

var WebsiteBackend = require('website.backendDashboard');

WebsiteBackend.include({

    events: _.defaults({
        'click tr.o_product_template': 'on_product_template',
    }, WebsiteBackend.prototype.events),

    init: function(parent, context) {
        this._super(parent, context);

        this.dashboards_templates.push('website_sale.dashboard_sales');
        this.graphs.push({'name': 'sales', 'group': 'sale_salesman'});
    },

    on_product_template: function(ev) {
        ev.preventDefault();

        var product_id = $(ev.currentTarget).data('productId');
        this.do_action({
            type: 'ir.actions.act_window',
            res_model: 'product.product',
            res_id: product_id,
            views: [[false, 'form']],
            target: 'current',
        }, {
            on_reverse_breadcrumb: this.on_reverse_breadcrumb,
        });
    },
});

});
