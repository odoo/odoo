/*
Purpose : show toggle button on depreciation/installment lines for posted/unposted line.
Details : called in list view with "<button name="create_move" type="object" widget="widgetonbutton"/>",
    this will call the method create_move on the object account.asset.depreciation.line
*/

odoo.define('account_asset.posting_button', function (require) {

    "use strict"; 
    
    var core = require('web.core');
    var session = require('web.session');

    var Column = core.list_widget_registry.get('field');
    var QWeb = core.qweb;

    var WidgetOnButton = Column.extend({
        format: function (row_data, options) {
            this._super(row_data, options);
            this.has_value = !!row_data.move_check.value;
            this.parent_state = row_data.parent_state.value;
            this.icon = this.has_value ? 'gtk-yes' : 'gtk-no'; // or STOCK_YES and STOCK_NO
            this.string = this.has_value ? 'Posted' : 'Unposted' 
            var template = this.icon && 'ListView.row.buttonwidget';
            return QWeb.render(template, {
                widget: this,
                prefix: session.prefix,
                disabled: this.has_value,
                invisible : true ? this.parent_state !== 'open' : false
            });
        },
    });
    core.list_widget_registry.add("button.widgetonbutton", WidgetOnButton);
});
