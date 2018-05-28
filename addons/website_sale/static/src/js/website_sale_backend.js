odoo.define('website_sale.backend', function (require) {
"use strict";

var WebsiteBackend = require('website.backend.dashboard');

WebsiteBackend.include({
    events: _.defaults({
        'click tr.o_product_template': 'on_product_template',
    }, WebsiteBackend.prototype.events),

    init: function (parent, context) {
        this._super(parent, context);

        this.graphs.push({'name': 'sales', 'group': 'sale_salesman'});
    },

    on_product_template: function (ev) {
        ev.preventDefault();

        var product_tmpl_id = $(ev.currentTarget).data('productId');
        this.do_action({
            type: 'ir.actions.act_window',
            res_model: 'product.template',
            res_id: product_tmpl_id,
            views: [[false, 'form']],
            target: 'current',
        }, {
            on_reverse_breadcrumb: this.on_reverse_breadcrumb,
        });
    },
});
return WebsiteBackend;

});
