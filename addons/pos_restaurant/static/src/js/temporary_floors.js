odoo.define('pos_restaurant.floors', function(require) {
    'use strict';

    var models = require('point_of_sale.models');

    var _super_order = models.Order.prototype;
    models.Order = models.Order.extend({
        initialize: function() {
            _super_order.initialize.apply(this, arguments);
            this.customer_count = this.customer_count || 1;
            this.save_to_db();
        },
        export_as_JSON: function() {
            var json = _super_order.export_as_JSON.apply(this, arguments);
            json.customer_count = this.customer_count;
            return json;
        },
        init_from_JSON: function(json) {
            _super_order.init_from_JSON.apply(this, arguments);
            this.customer_count = json.customer_count || 1;
        },
        export_for_printing: function() {
            var json = _super_order.export_for_printing.apply(this, arguments);
            json.customer_count = this.get_customer_count();
            return json;
        },
        get_customer_count: function() {
            return this.customer_count;
        },
        set_customer_count: function(count) {
            this.customer_count = Math.max(count, 0);
            this.trigger('change');
        },
    });
});
