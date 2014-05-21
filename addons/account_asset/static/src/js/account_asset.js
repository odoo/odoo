openerp.account_asset = function (instance) {
    var _t = instance.web._t,
        _lt = instance.web._lt;
    var QWeb = instance.web.qweb;
    instance.web.list.WidgetOnButton = instance.web.list.Column.extend({
        format: function (row_data, options) {
            this._super(row_data, options);
            this.has_value = !!row_data.move_check.value;
            this.parent_state = row_data.parent_state.value;
            this.icon = this.has_value ? 'gtk-yes' : 'gtk-no';
            this.string = this.has_value ? 'Posted' : 'Unposted' 
            var template = this.icon && 'ListView.row.buttonwidget';
            return QWeb.render(template, {
                widget: this,
                prefix: instance.session.prefix,
                disabled: this.has_value,
                invisible : 'true' ? this.parent_state !== 'open' : 'false'
            });
        },
    });
    instance.web.list.columns.add("button.widgetonbutton", "instance.web.list.WidgetOnButton");
};