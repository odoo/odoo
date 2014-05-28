openerp.base.language = function (instance) {
    var _t = instance.web._t,
        _lt = instance.web._lt;
    var QWeb = instance.web.qweb;
    instance.web.list.Lang_Activation = instance.web.list.Column.extend({
        format: function (row_data, options) {
            this._super(row_data, options);
            this.has_value = !!row_data.active.value;
            this.icon = this.has_value ? 'gtk-yes' : 'gtk-no';
            this.string = this.has_value ? 'Click here to disable language' : 'Click here to enable language'
            var template = this.icon && 'ListView.row.buttonwidget';
            return QWeb.render(template, {
                widget: this,
                prefix: instance.session.prefix,
            });
        },
    });
    instance.web.list.columns.add("button.lang_activation", "instance.web.list.Lang_Activation");

    instance.web.form.Lang_Activaton_Button = instance.web.form.AbstractField.extend({
        template: 'LangActivationButton',
        render_value: function() {
            this._super();
            this.$("button:first")
                .toggleClass("btn-success", this.get_value())
                .toggleClass("btn-danger", !this.get_value());
            this.$('ul.dropdown-menu li a.js_publish_btn')
                .toggleClass("enabled", this.get_value())
                .toggleClass("disabled", !this.get_value());
        },
        start: function() {
            var self = this;
            this._super.apply(this, arguments);
            this.$("button:first")
                .on("click", function () {
                    self.set_value(!!$(this).hasClass("btn-danger"));
                    return self.view.recursive_save();
            });
            this.$('ul.dropdown-menu li a.js_publish_btn')
                .on("click", function () {
                    self.set_value(!!$(this).hasClass("disabled"));
                    return self.view.recursive_save();
            });
        },
    });

    instance.web.form.widgets = instance.web.form.widgets.extend({
        'lang_activation_button': 'instance.web.form.Lang_Activaton_Button',
    });
};