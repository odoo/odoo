odoo.define('website_sale.backend', function (require) {
"use strict";

var core = require('web.core');
var WebsiteBackend = require('website.backendDashboard');

var QWeb = core.qweb;

WebsiteBackend.include({
    events: _.defaults({
        'click tr.o_product_template': 'on_product_template',
    }, WebsiteBackend.prototype.events),

    init: function(parent, context) {
        this._super(parent, context);

        this.graphs.push({'name': 'sales', 'group': 'sale_salesman'});
    },
    render_dashboards: function() {
        this._super()
        this.$('.o_dashboard_common').after(QWeb.render('website_sale.dashboard_sales', {widget: this}));
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
