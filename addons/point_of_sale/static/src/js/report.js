odoo.define('point_of_sale.report', function (require) {
"use strict";

var chat_manager = require('mail.chat_manager');
var composer = require('mail.composer');
var ChatThread = require('mail.ChatThread');
var utils = require('mail.utils');

var config = require('web.config');
var core = require('web.core');
var data = require('web.data');
var Dialog = require('web.Dialog');
var framework = require('web.framework');
var Model = require('web.Model');

var pyeval = require('web.pyeval');
var SearchView = require('web.SearchView');

var ActionManager = require('web.ActionManager');
var ControlPanelMixin = require('web.ControlPanelMixin');
var datepicker = require('web.datepicker');
var Widget = require('web.Widget');

var QWeb = core.qweb;
var _t = core._t;

// TODO replace in v10 with proper wizard
var PosDetailsWidget = Widget.extend(ControlPanelMixin, {
    template: 'WizardSaleDetailsReport',
    events: {
        "click .js_generate": "renderReport",
    },

    renderElement: function() {
        this._super();

        var current_date = new moment();
        this.dp_start = new datepicker.DateWidget(this);
        this.dp_start.insertBefore(this.$el.find('.js_date_start'));
        this.dp_start.set_value(current_date.format('YYYY-MM-DD'));

        this.dp_stop = new datepicker.DateWidget(this);
        this.dp_stop.insertAfter(this.$el.find('.js_date_stop'));
        this.dp_stop.set_value(current_date.format('YYYY-MM-DD'));

    },

    renderReport: function() {
        var start = this.dp_start.get_value();
        var stop = this.dp_stop.get_value();
        var url = '/pos/sale_details_report?date_start='+start+'&date_stop='+stop;
        window.open(url, '_blank');

    },

});


core.action_registry.add('report_pos_details', PosDetailsWidget);

return PosDetailsWidget;

});
