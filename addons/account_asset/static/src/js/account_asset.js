/*
Purpose : show toggle button on depreciation/installment lines for posted/unposted line.
Details : called in list view with "<button name="create_move" type="object" widget="widgetonbutton"/>",
    this will call the method create_move on the object account.asset.depreciation.line
*/

odoo.define('account_asset.widget', function(require) {
"use strict";

var core = require('web.core');
var QWeb = core.qweb;
var session = require('web.session');

var _t = core._t;

var WidgetOnButton = core.list_widget_registry.get('field').extend({
    format: function(row_data, options) {
        this._super.apply(this, arguments);
        this.has_value = !!row_data.move_check.value;
        this.parent_state = row_data.parent_state.value;

        return $('<div/>').append((this.parent_state === 'open')? $('<button/>', {
            type: 'button',
            title: (this.has_value)? _t('Posted') : _t('Unposted'),
            disabled: !!this.has_value,
            'class': 'btn btn-sm btn-link fa fa-circle o_widgetonbutton' + ((this.has_value)? ' o_has_value' : ''),
        }) : '').html();
    },
});

core.list_widget_registry.add("button.widgetonbutton", WidgetOnButton);
});
