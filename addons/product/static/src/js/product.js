openerp.product = function (instance) {
instance.web.form.widgets.add('uom_factor', 'instance.web.form.FieldUOMFactor');
instance.web.form.FieldUOMFactor = instance.web.form.FieldFloat.extend({
    template: "FieldUOMFactor",
    init: function() {
        this._super.apply(this, arguments);
        this.set({"category": false, 'name': false});
        if (this.options.category_field) {
            this.field_manager.on("field_changed:" + this.options.category_field, this, function() {
                this.set({"category": this.field_manager.get_field_value(this.options.category_field)});
            });
        }
        if (this.options.name_field) {
            this.field_manager.on("field_changed:" + this.options.name_field, this, function() {
                this.set({"name": this.field_manager.get_field_value(this.options.name_field)});
            });
        }
        this.on("change:category", this, this.get_uom_reference);
        this.get_uom_reference();
        this.ci_dm = new instance.web.DropMisordered();
    },
    start: function() {
        var tmp = this._super();
        this.on("change:uom_reference", this, this.reinitialize);
        this.on("change:name", this, this.reinitialize);
        return tmp;
    },
    get_uom_reference: function() {
        var self = this;
        if (this.get("category") === false) {
            this.set({"uom_reference": null});
            return;
        }
        return this.ci_dm.add(new instance.web.Model("product.uom").query(["name"])
            .filter([["category_id", "=", self.get("category")],["uom_type", "=", "reference"]]).first()).pipe(function(res) {
               self.set({"uom_reference": res});
        });
    },
    parse_value: function(val, def) {
        return instance.web.parse_value(val, {type: "float"}, def);
    },
    format_value: function(val, def) {
        return instance.web.format_value(val, {type: "float"}, def);
    },
});
}
