odoo.define('lunch.previous_orders', function (require) {
"use strict";

var core = require('web.core');
var field_utils = require('web.field_utils');
var field_registry = require('web.field_registry');
var relational_fields = require('web.relational_fields');
var QWeb = core.qweb;

var FieldMany2Many = relational_fields.FieldMany2Many;

var LunchPreviousOrdersWidget = FieldMany2Many.extend({
    className: 'row o_lunch_last_orders',
    events: {
        'click .o_add_button': 'set_order_line',
    },
    init: function() {
        this._super.apply(this, arguments);
        this.lunch_data = {};
        this.fields_to_read = ['product_id', 'supplier', 'note', 'price', 'category_id', 'currency_id'];
        this.format_value = function (value) {
            var options = _.extend({}, this.nodeOptions, { data: this.recordData });
            return field_utils.format.monetary(value, this.field, options);
        };
    },
    get_line_value: function(id) {
        var data = _.clone(this.lunch_data[id]);
        if (typeof this.lunch_data[id].product_id[0] !== 'undefined'){
            data.product_id = this.lunch_data[id].product_id[0];
        }
        if (typeof this.lunch_data[id].supplier[0] !== 'undefined'){
            data.supplier = this.lunch_data[id].supplier[0];
        }
        if (typeof this.lunch_data[id].category_id[0] !== 'undefined'){
            data.category_id = this.lunch_data[id].category_id[0];
        }
        return data;
    },
    set_order_line: function() {
        // FIXME: This is the true functionality of this widget in edit mode
        // var data = this.get_line_value(parseInt($(event.currentTarget).data('id')));
        // var order_line_ids = this.field_manager.fields.order_line_ids;
        // order_line_ids.data_create(data);
        // order_line_ids.reload_current_view();
    },
    render: function() {
        var self = this;
        // Fetch values
        // FIXME: this might be replaced when we implement a way for widgets
        //        to declare which fields they need from the relational data
        this.trigger_up('perform_model_rpc', {
            model: 'lunch.order.line',
            method: 'read',
            args: [
                this.value,
                this.fields_to_read
            ],
            on_success: function (orders) {
                if (_.isEmpty(orders)) {
                    self.$el.html(QWeb.render("LunchPreviousOrdersWidgetNoOrder"));
                } else {
                    _.each(orders, function(order) {
                        self.lunch_data[order.id] = order;
                    });
                    var categories = _.groupBy(orders, function(o){ return o.supplier[1]; });
                    return self.$el.html(QWeb.render("LunchPreviousOrdersWidgetList", {'widget': self, 'categories': categories}));
                }
            }
        });
    },
    has_no_value: function() {
        return false;
    },
});

field_registry.add('previous_order', LunchPreviousOrdersWidget);

return LunchPreviousOrdersWidget;

});
