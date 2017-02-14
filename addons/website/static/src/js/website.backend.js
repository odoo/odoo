openerp.website = function(instance) {
var _t = instance.web._t;

instance.web.form.WidgetWebsiteButton = instance.web.form.AbstractField.extend({
    template: 'WidgetWebsiteButton',
    render_value: function() {
        this._super();
        this.$("button:first")
            .toggleClass("btn-success", this.get_value())
            .toggleClass("btn-danger", !this.get_value());
        this.$("a:first").attr("href", this.view.datarecord.website_url || "/" );
        if (this.node.attrs.class) {
            this.$el.addClass(this.node.attrs.class);
        }
    },
    start: function() {
        var self = this;
        this._super.apply(this, arguments);

        this.$('#dopprod-0').on('click', function() {
            self.render_value();
        });
        this.$("button:first").on("click", function () {
            console.log("click", !!$(this).hasClass("btn-danger"));
            self.set_value(!!$(this).hasClass("btn-danger"));
            return self.view.recursive_save();
        });
    },
});

instance.web.form.widgets = instance.web.form.widgets.extend({
    'website_button': 'instance.web.form.WidgetWebsiteButton',
});

};
