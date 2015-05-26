/*
Purpose : show toggle button on depreciation/installment lines for posted/unposted line.
Details : called in list view with "<button name="create_move" type="object" widget="widgetonbutton"/>",
    this will call the method create_move on the object account.asset.depreciation.line
*/

odoo.define('account_asset.widget', function(require) {
"use strict";

// openerp.account_asset = function (instance) {
    // var _t = instance.web._t,
    //     _lt = instance.web._lt;
    // var QWeb = instance.web.qweb;
    // instance.web.account_asset = instance.web.account_asset || {};

var core = require('web.core');
var QWeb = core.qweb;
var list_widget_registry = core.list_widget_registry;
var Column = list_widget_registry.get('field');

var WidgetOnButton = Column.extend({
    format: function (row_data, options) {
        this._super(row_data, options);
        this.has_value = !!row_data.move_check.value;
        this.parent_state = row_data.parent_state.value;
        this.icon = this.has_value ? 'gtk-yes' : 'gtk-no'; // or STOCK_YES and STOCK_NO
        this.string = this.has_value ? 'Posted' : 'Unposted';
        var template = this.icon && 'ListView.row.buttonwidget';
        return QWeb.render(template, {
            widget: this,
            prefix: instance.session.prefix,
            disabled: this.has_value,
            invisible : true ? this.parent_state !== 'open' : false
        });
    },
});

list_widget_registry.add("button.widgetonbutton", WidgetOnButton);
});
