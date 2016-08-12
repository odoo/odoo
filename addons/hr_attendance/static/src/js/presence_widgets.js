odoo.define('hr_attendance.presence_widgets', function (require) {
"use strict";

var core = require('web.core');
var form_common = require('web.form_common');
var kanban_widgets = require('web_kanban.widgets');

var QWeb = core.qweb;
var _t = core._t;

var FormPresenceIndicator = form_common.AbstractField.extend({
    init: function() {
        this._super.apply(this, arguments);
    },
    start: function() {
        this.display_field();
        // this.render_value();  -> gets called automatically in form_common.AbstractField
        this.$el.tooltip({title: _t("employee presence<br/>green: checked in<br/>red: checked out"), trigger: 'hover'});
        return this._super();
    },
    render_value: function() {
        this.$('.oe_hr_attendance_status').toggleClass("oe_hr_attendance_status_green", this.get_value() == 'checked_in');
        this.$('.oe_hr_attendance_status').toggleClass("oe_hr_attendance_status_red", this.get_value() == 'checked_out');
    },
    display_field: function() {
        this.$el.html(QWeb.render("PresenceIndicator"));
    },
});

var KanbanPresenceIndicator = kanban_widgets.AbstractField.extend({
    init: function() {
        this._super.apply(this, arguments);
    },
    start: function() {
        this.display_field();
        this.render_value(); // doesn't get called automatically in kanban_widgets.AbstractField
        this.$el.tooltip({title: _t("employee presence<br/>green: checked in<br/>red: checked out"), trigger: 'hover'});
        return this._super();
    },
    render_value: function() {
        this.$('.oe_hr_attendance_status').toggleClass("oe_hr_attendance_status_green", this.field.raw_value == 'checked_in');
        this.$('.oe_hr_attendance_status').toggleClass("oe_hr_attendance_status_red", this.field.raw_value == 'checked_out');
    },
    display_field: function() {
        this.$el.html(QWeb.render("PresenceIndicator"));
    },
});

core.form_widget_registry.add('hr_attendance_form_presence_indicator', FormPresenceIndicator);
kanban_widgets.registry.add('hr_attendance_kanban_presence_indicator', KanbanPresenceIndicator);

});