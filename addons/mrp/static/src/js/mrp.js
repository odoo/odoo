odoo.define('mrp.mrp', function (require){

var core = require('web.core');
var formats = require('web.formats');
var Model = require('web.Model');
var FieldFloat = core.form_widget_registry.get('float');

var _t = core._t;

var mrp_product_qty = FieldFloat.extend({
    init: function(field_manager, node) {
        var self = this;
        this._super(field_manager, node);
        this.on("change:value", this, function() {
            self.update_label(this.get('value'));
        });
        var $page = this.view.$el.find("a[name='consumed_products']");
        var $label_product = this.view.$el.find("div[name='group_to_consume']");
        var $label_consumed = this.view.$el.find("div[name='group_consumed']");
        var $wizard_page = this.view.$el.find("div[name='produce']");
        this.label_list = [$page, $label_product, $label_consumed, $wizard_page];
        this.label_value = [[_t("Consumed Products"), _t("Disassembled Products")],
                            [_t("Products to Consume"), _t("Products to Disassemble")],
                            [_t("Consumed Products"), _t("Disassembled Products")],
                            [_t("Produce"), _t("Product to Disassemble")]];
    },
    update_label:function(value){
        var self = this
        new Model("mrp.production").call('read', [this.view.dataset.context.active_id, ['id', 'product_qty']]).then(function(result){
            if (result.product_qty <= 0){
                _.map(self.label_list, function(ele, i){
                    ele.text(self.label_value[i][1])
                });
            } else {
                _.map(self.label_list, function(ele, i){
                    value >= 0 ? ele.text(self.label_value[i][0]) : ele.text(self.label_value[i][1])
                });
            }
        });
    },
    parse_value: function(val, def) {
        if (this.widget) this.widget='float'
        return formats.parse_value(val, this, def);
    },
    format_value: function(val, def) {
        if (this.widget) this.widget='float'
        return formats.format_value(val, this, def);
    },

    });
core.form_widget_registry.add('mrp_product_qty', mrp_product_qty)
});
