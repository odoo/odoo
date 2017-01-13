odoo.define('lunch.form_widgets', function (require) {
"use strict";

var core = require('web.core');
var form_common = require('web.form_common');
var form_widgets = require('web.form_widgets');
var form_relational = require('web.form_relational');
var _t = core._t;
var QWeb = core.qweb;

var LunchPreviousOrdersWidget = form_relational.AbstractManyField.extend(form_common.ReinitializeWidgetMixin, {
    className: 'row o_lunch_last_orders',
    events: {
        'click .o_add_button': 'set_order_line',
    },
    init: function(field_manager, node) {
        this._super.apply(this, arguments);
        this.lunch_data = {};
        this.fields_to_read = ['product_id', 'supplier', 'note', 'price', 'category_id', 'currency_id'];
        this.monetary = new form_widgets.FieldMonetary(field_manager, node); // create instance to use format_value
        this.monetary.__edispatcherRegisteredEvents = []; // remove all bind events
    },
    fetch_value: function(){
        var self = this;
        return this.dataset.read_ids(this.get('value'), this.fields_to_read)
            .then(function(data) {
                _.each(data, function(order) {
                    self.lunch_data[order['id']] = order;
                });
                return data;
            });
    },
    get_line_value: function(id) {
        var data = _.clone(this.lunch_data[id]);
        if (typeof this.lunch_data[id]['product_id'][0] != 'undefined'){
            data['product_id'] = this.lunch_data[id]['product_id'][0];
        }
        if (typeof this.lunch_data[id]['supplier'][0] != 'undefined'){
            data['supplier'] = this.lunch_data[id]['supplier'][0];
        }
        if (typeof this.lunch_data[id]['category_id'][0] != 'undefined'){
            data['category_id'] = this.lunch_data[id]['category_id'][0];
        }
        return data;
    },
    set_order_line: function(event) {
        var data = this.get_line_value(parseInt($(event.currentTarget).data('id')));
        var order_line_ids = this.field_manager.fields.order_line_ids;
        order_line_ids.data_create(data);
        order_line_ids.reload_current_view();
    },
    render_value: function() {
        var self = this;
        return this.fetch_value().then(function(data) {
            if (_.isEmpty(data)) {
                return self.$el.html(QWeb.render("lunch_order_widget_no_previous_order"));
            }
            var categories = _.groupBy(data,function(data1){return data1['supplier'][1];});
            return self.$el.html(QWeb.render("lunch_order_widget_previous_orders_list", {'widget': self, 'categories': categories}));
        });
    },
    destroy: function() {
        this.monetary.destroy();
        this._super();
    },
    is_false: function() {
        return false;
    },
});

core.form_widget_registry.add('previous_order', LunchPreviousOrdersWidget);

return LunchPreviousOrdersWidget;

});
