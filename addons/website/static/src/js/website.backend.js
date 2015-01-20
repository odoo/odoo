openerp.website = function(instance) {
var _t = instance.web._t;

instance.web.form.WidgetWebsiteButton = instance.web.form.AbstractField.extend({
    template: 'WidgetWebsiteButton',
    render_value: function() {
        this._super();
        this.$()
            .toggleClass("success", this.get_value())
            .toggleClass("danger", !this.get_value());
        if (this.node.attrs.class) {
            this.$el.addClass(this.node.attrs.class);
        }
    },
});

instance.web.form.widgets = instance.web.form.widgets.extend({
    'website_button': 'instance.web.form.WidgetWebsiteButton',
});

};
