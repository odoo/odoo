odoo.define('web.kanban.activity', function (require) {
"use strict";

var core = require('web.core');
var Model = require("web.Model");
var Widget = require('web.Widget');
var kanban_widgets = require('web_kanban.widgets');
var AbstractField = kanban_widgets.AbstractField;
var fields_registry = kanban_widgets.registry;
var set_delay_label = require('mail.activity').set_delay_label;

var QWeb = core.qweb;


var KanbanActivity = AbstractField.extend({
    template: 'mail.KanbanActivity',

    events: {
        "click .o_activity_btn": "get_activity_logs",
        "click .o_schedule_activity": "on_activity_schedule",
        "click .o_mark_as_done": "on_activity_done",
    },

    init: function(parent, field, $node) {
        this._super.apply(this, arguments);
        this.parent = parent;
        this.activity_state = parent.record.activity_state.raw_value;
        this.selection = _.object(parent.fields.activity_state.selection);
        this.Activity = new Model("mail.activity");
    },

    get_activity_logs: function(event) {
        event.preventDefault();
        var self = this;
        this.$('.o_activity').html(QWeb.render("mail.KanbanActivityLoading"));
        this.Activity
            .call("read", [this.field.raw_value])
            .then(function (records) {
                records = set_delay_label(records);
                self.$('.o_activity').html($(QWeb.render("mail.KanbanActivityDropdown", {
                    selection: self.selection,
                    records: _.groupBy(records, 'state'),
                    uid: self.session.uid,
                })));
            });
    },

    reset_state: function () {
        var self = this;
        new Model(self.parent.model).query(['activity_ids', 'activity_state'])
            .filter([['id', '=', self.parent.id]])
            .first()
            .then(function (record) {
                var state_color_class =  'o_activity_color_' + (record.activity_state || 'default');
                var current_state_class = 'o_activity_color_' + (self.activity_state || 'default');
                self.$(".o_activity_btn > span").removeClass(current_state_class).addClass(state_color_class);
                self.activity_state = record.activity_state;
                self.parent.record.activity_ids.raw_value = record.activity_ids;
            });
    },

    on_activity_schedule: function(event) {
        var self = this;
        var activity_id = this.$(event.currentTarget).data('activity-id') || false;
        var action = {
            type: 'ir.actions.act_window',
            res_model: 'mail.activity',
            view_mode: 'form',
            view_type: 'form',
            views: [
                [false, 'form']
            ],
            target: 'new',
            context: _.extend({
                default_res_id: this.parent.id,
                default_res_model: this.parent.model,
            }, {'mark_done': true}, this.context),
            res_id: activity_id,
        };
        this.do_action(action, {
            on_close: function() {
                self.reset_state();
                self.get_activity_logs(event);
            }
        });
    },

    on_activity_done: function (event) {
        event.stopPropagation();
        var self = this;
        var activity_id = this.$(event.currentTarget).data('activity-id');
        this.Activity
            .call("action_done", [[activity_id]])
            .then(function (result) {
                self.get_activity_logs(event);
                self.reset_state();
            });
    },
});

fields_registry.add('kanban_activity', KanbanActivity);

return {
    KanbanActivity: KanbanActivity
};
});
