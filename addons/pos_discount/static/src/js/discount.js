odoo.define('pos_discount.pos_discount', function (require) {
"use strict";

var core = require('web.core');
var screens = require('point_of_sale.screens');
var models = require('point_of_sale.models');

var _t = core._t;

var existing_models = models.PosModel.prototype.models;
var product_index = _.findIndex(existing_models, function (model) {
    return model.model === "product.product";
});
var product_model = existing_models[product_index];

models.load_models({
    model:  product_model.model,
    fields: product_model.fields,
    order:  product_model.order,
    domain: function(self){
        return [['id', '=', self.config.discount_product_id[0]]];
    },
    context: product_model.context,
    loaded: function(self, discount_product){
        if (discount_product[0]) {
            self.global_discount_product_id = discount_product[0].id;
            if (self.db.get_product_by_id(self.global_discount_product_id) === undefined) {
                self.db.product_by_id[self.global_discount_product_id] = new models.Product({}, discount_product[0]);
            }
        }
    },
});

var _super_orderline = models.Orderline.prototype;
models.Orderline = models.Orderline.extend({
    initialize: function(attr, options) {
        _super_orderline.initialize.call(this, attr, options);
        var id = options.json ? options.json.id : options.product.id;
        if (!this.is_discount_line) {
            this.listenTo(this, 'change', function(){
                var order = this.order;
                if (order.global_discount) {
                    order.recompute_global_discount();
                }
            });
        }
    },
});

var _super_order = models.Order.prototype;
models.Order = models.Order.extend({
    export_as_JSON: function() {
        var json = _super_order.export_as_JSON.call(this);
        json.global_discount = this.global_discount;
        return json;
    },
    init_from_JSON: function(json) {
        _super_order.init_from_JSON.call(this, json);
        if (this.pos.config.module_pos_discount) {
            this.global_discount = json.global_discount || false;
            this.set_global_discount(this.global_discount)
        }
    },
    add_global_discount_lines: function() {
        var self = this;
        var product  = this.pos.db.get_product_by_id(this.pos.global_discount_product_id);
        if (product === undefined) {
            this.gui.show_popup('error', {
                title : _t("No discount product found"),
                body  : _t("The discount product seems misconfigured."),
            });
            return;
        }
        var grp = {}
        var lines    = this.get_orderlines();
        lines.forEach(function(line){
            var key = line.product.taxes_id || "-1"
            grp[key] = (grp[key] || 0) + line.get_price_without_tax();
        });

        // Add discount
        // We add the price as manually set to avoid recomputation when changing customer.
        Object.keys(grp).forEach(function(key){
            var discount = - self.global_discount / 100 * grp[key];
            if (discount < 0 || discount > 0) {
                var prod = $.extend(true, {}, product);
                if (key == "") {
                    prod.taxes_id = [];
                } else {
                    prod.taxes_id = key.split(',').map(Number);
                }

                self.add_product(prod, {
                    price: discount,
                    select: false,
                    is_discount_line: true,
                });
            };
        });
    },
    remove_global_discount_lines: function() {
        var self = this;
        var to_remove = []
        this.get_orderlines().forEach(function(order_line){
            if (order_line.get_product().id === self.pos.global_discount_product_id) {
                to_remove.push(order_line);
            }
        })
        to_remove.forEach(function(order_line){
            self.remove_orderline(order_line, false);
        })
    },
    set_global_discount: function(percentage) {
        if (percentage && percentage > 0) {
            this.global_discount = percentage;
        } else {
            this.global_discount = false;
        }
        if (this.pos.chrome.screens) {
            this.pos.chrome.screens.products.action_buttons.discount.renderElement();
        }
        this.recompute_global_discount();
    },
    recompute_global_discount: function() {
        var buffer = this.pos.chrome.screens ? this.pos.chrome.screens.products.numpad.state.get("buffer"): false;
        this.remove_global_discount_lines();
        if (this.global_discount) {
            this.add_global_discount_lines();
        }
        if (buffer !== false) {
            this.pos.chrome.screens.products.numpad.state.set({buffer: buffer});
        }
    },
    get_last_orderline: function(){
        var self = this;
        if (!this.global_discount){
            return _super_order.get_last_orderline.call(this)
        } else {
            var last_orderline = false;
            this.orderlines.models.reverse().some(function(orderline){
                if (orderline.product.id !== self.pos.global_discount_product_id) {
                    last_orderline = orderline;
                    return true;
                }
                return false;
            });
            this.orderlines.models.reverse();
            return last_orderline;
        }
    },
    select_orderline: function(line){
        if (line && line.product.id !== this.pos.global_discount_product_id) {
            _super_order.select_orderline.call(this, line);
        }
    }
})

screens.ScreenWidget.include({
    barcode_product_action: function(code){
        var self = this;
        var discount_product = this.pos.db.get_product_by_id(this.pos.global_discount_product_id);
        if (discount_product.barcode && code.base_code === discount_product.barcode){
            this.gui.show_popup('number',{
                'title': _t('Discount Percentage'),
                'value': this.pos.get_order().global_discount || this.pos.config.discount_pc,
                'confirm': function(val) {
                    val = Math.max(0,Math.min(100,val));
                    self.pos.get_order().set_global_discount(val);
                },
            });
        } else {
            this._super(code);
        }
    },
    show: function() {
        this._super();
        this.pos.barcode_reader.action_callback['product'] =  _.bind(this.barcode_product_action, this);
    }
});

var DiscountButton = screens.ActionButtonWidget.extend({
    template: 'DiscountButton',
    init: function(parent, options) {
        this._super(parent,options);
        this.pos.bind('change:selectedOrder', function () {
            this.renderElement();
        }, this);
    },
    renderElement: function(){
        var self = this;
        this._super();
        var order = this.pos.get_order()
        if (order && order.global_discount) {
            $(self.$el).addClass('discount_selected');
        } else {
            $(self.$el).removeClass('discount_selected');
        }
    },
    button_click: function(){
        var self = this;
        this.gui.show_popup('number',{
            'title': _t('Discount Percentage'),
            'value': this.pos.get_order().global_discount || this.pos.config.discount_pc,
            'confirm': function(val) {
                val = Math.max(0,Math.min(100,val));
                self.pos.get_order().set_global_discount(val);
            },
        });
    },
});

screens.define_action_button({
    'name': 'discount',
    'widget': DiscountButton,
    'condition': function(){
        return this.pos.config.module_pos_discount && this.pos.config.discount_product_id;
    },
});

return {
    DiscountButton: DiscountButton,
}

});
