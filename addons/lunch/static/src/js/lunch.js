odoo.define('lunch.previous_orders', function (require) {
"use strict";

var core = require('web.core');
var form_common = require('web.form_common');
var formats = require('web.formats');
var Model = require('web.Model');

var QWeb = core.qweb;

var LunchPreviousOrdersWidget = form_common.AbstractField.extend({
    events: {
        'click .o_add_button': 'add_order_line',
    },
    render_value: function() {
        this.lunch_data = JSON.parse(this.get('value'));
        if (this.lunch_data !== false) {
            // Similar to format_value of FieldMonetary
            _.each(this.lunch_data, function(k, v) {
                k.price_format = formats.format_value(k.price, {type: "float", digits: k.digits});
            });

            // Group data by supplier for display
            var categories = _.groupBy(this.lunch_data, function(p) {
                return p['supplier'];
            });
            this.$el.html(QWeb.render('LunchPreviousOrdersWidgetList', {'categories': categories}));
        } else {
            return this.$el.html(QWeb.render('LunchPreviousOrdersWidgetNoOrder'));
        }
    },
    add_order_line: function(event) {
        // Get order details from line
        var line_id = parseInt($(event.currentTarget).data('id'));
        if (!line_id) {
            return;
        }
        var values = {
            'product_id': this.lunch_data[line_id].product_id,
            'note': this.lunch_data[line_id].note,
            'price': this.lunch_data[line_id].price,
        }

        // Create new order line and reload view
        var order_line_ids = this.field_manager.fields.order_line_ids;
        order_line_ids.data_create(values)
            .then(function (p) {
                order_line_ids.reload_current_view();
            }
        );
    },
});

core.form_widget_registry.add('previous_order', LunchPreviousOrdersWidget);

});
