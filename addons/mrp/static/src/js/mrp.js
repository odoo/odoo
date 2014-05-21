openerp.mrp = function(instance) {
var _t = instance.web._t;

instance.web.form.mrp_product_qty =  instance.web.form.FieldFloat.extend({
    init: function(field_manager, node) {
        var self = this;
        this._super(field_manager, node);
        this.on("change:value", this, function() {
            self.update_label(this.get('value'));
        });
        var $page = this.view.$el.find("a[name='consumed_products']");
        var $label_product = this.view.$el.find("div[name='group_to_consume']");
        var $label_consumed = this.view.$el.find("div[name='group_consumed']");
        this.label_list = [$page, $label_product, $label_consumed];
        this.label_value = [[_t("Consumed Products"),_t("Disassembled Products")],
                            [_t("Products to Consume"),_t("Products to Disassemble")],
                            [_t("Consumed Products"),_t("Disassembled Products")]];
    },
    update_label:function(value){
        var self = this
        _.map(self.label_list, function(ele, i){ 
            value > 0 ? ele.text(self.label_value[i][0]) : ele.text(self.label_value[i][1])
        });
    },			
    parse_value: function(val, def) {
        if (this.widget) this.widget='float'
        return instance.web.parse_value(val, this, def);
    },
    format_value: function(val, def) {
        if (this.widget) this.widget='float'
        return instance.web.format_value(val, this, def);
    },

});
instance.web.form.widgets = instance.web.form.widgets.extend({
'mrp_product_qty': 'instance.web.form.mrp_product_qty',
});
}