odoo.define('mail.kanban_activity', function (require) {
"use strict";

var core = require('web.core');
var kanban_widgets = require('web_kanban.widgets');
var Model = require('web.Model');
var ActivityLog = require('mail.ActivityLog');


var AbstractField = kanban_widgets.AbstractField;
var fields_registry = kanban_widgets.registry;
var QWeb = core.qweb;

/**
 * Kanban widgets: Activity
 **/

var KanbanActivity = AbstractField.extend({
    template: 'KanbanActivity',
    events: {
        "click .o_activity_logs": "get_activity_logs",
        "click .o_schedule_activity": "on_open_schedule_activity",
        "click .o_mark_as_done": "on_mark_as_done",
    },
    init: function(parent, field, $node) {
        this._super.apply(this, arguments);
        this.parent = parent;
        this.activity = new ActivityLog(parent.id, parent.model);
        this.activity_state = parent.record.activity_state.raw_value;
        this.selection = _.object(parent.fields.activity_state.selection);
    },

    get_activity_logs: function(event) {
        event.preventDefault();
        var self = this;
        self.$('.o_activity').html(QWeb.render("KanbanActivityLoading"));
        self.activity.fetch_activities()
            .then(function(records) {
                self.$('.o_activity').html($(QWeb.render("KanbanActivityDropdown", {
                    selection: self.selection,
                    records: _.groupBy(records, 'state')
                })));
            });
    },
    on_open_schedule_activity: function(event) {
        var self = this,
            activity_id = this.$(event.currentTarget).data('activity-id') || false,
            action = this.activity.add_activity_action(activity_id);
        this.do_action(action, {
            on_close: function() {
                self.reset_state();
                self.get_activity_logs(event);
            }
        });
    },
    on_mark_as_done: function (event) {
        event.preventDefault();
        event.stopPropagation();
        var self = this,
            activity_id =  this.$(event.currentTarget).data('activity-id') || false;
        this.activity.mark_as_done(activity_id)
            .then(function (result) {
                self.get_activity_logs(event);
                self.reset_state();
            });
    },
    reset_state: function () {
        var self = this;
        new Model(self.parent.model).query(['activity_log_ids', 'activity_state'])
            .filter([['id', '=', self.parent.id]])
            .first()
            .then(function(record) {
                var state_color =  (record.activity_state) ? record.activity_state : 'default';
                self.$(".o_activity_logs > span").removeClass('o_activity_color_' + self.activity_state).addClass('o_activity_color_' + state_color);
                self.activity_state = record.activity_state;
                self.parent.record.activity_log_ids.raw_value = record.activity_log_ids;
            });
    }
});

fields_registry.add('kanban_activity', KanbanActivity);

});
