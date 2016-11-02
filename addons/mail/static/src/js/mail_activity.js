odoo.define('mail.ActivityLog', function (require) {
"use strict";

var core = require('web.core');
var Model = require("web.Model");
var Widget = require('web.Widget');
var chat_manager = require('mail.chat_manager');

var kanban_widgets = require('web_kanban.widgets');
var AbstractField = kanban_widgets.AbstractField;
var fields_registry = kanban_widgets.registry;

var QWeb = core.qweb;
var Class = core.Class;


var AbstractActivityLog = {
    init: function(res_id, res_model){
        this.res_id = res_id;
        this.res_model = res_model;
        this.limit = 10;  // TODO Add pager
        this.ActivityLogModel = new Model("mail.activity.log");
    },
    fetch_activities: function () {
        return this.ActivityLogModel
            .call("fetch_activity_logs", [this.res_id, this.res_model, this.limit || false]);
    },
    remove_activity_log: function (activity_id) {
        return this.ActivityLogModel.call("remove_activity_log", [activity_id]);
    },
    mark_as_done: function (activity_id) {
        return this.ActivityLogModel.call("mark_as_done", [activity_id]);
    },
    get_create_activity_action : function(activity_id){
        return {
            type: 'ir.actions.act_window',
            res_model: 'mail.activity.log',
            view_mode: 'form',
            view_type: 'form',
            views: [
                [false, 'form']
            ],
            target: 'new',
            context: _.extend({
                default_res_id: this.res_id,
                default_model: this.res_model,
            }, this.context),
            res_id: activity_id,
        };
    },
};


// -----------------------------------------------------------------------------
// Activity Log
//
// Integrated with Chatter
// -----------------------------------------------------------------------------
var ActivityLogList = Widget.extend(AbstractActivityLog, {
    events: {
        "click .o_edit_activity": "on_open_schedule_activity",
        "click .o_remove_activity": "on_remove_activity",
        "click .o_mark_as_done": "on_mark_as_done",
    },
    init: function(chatter, res_id, res_model){
        this.chatter = chatter;
        this._super.apply(this, arguments);
        AbstractActivityLog.init.call(this, res_id, res_model);
    },
    start: function () {
        this.fetch_and_render_activity_log();
    },
    on_open_schedule_activity: function(event){
        event.preventDefault();
        var self = this,
            activity_id = this.$(event.currentTarget).data('activity-id') || false,
            action = this.get_create_activity_action(activity_id);
        this.do_action(action, {
            on_close: function() {
                self.fetch_and_render_activity_log();
                self.chatter.refresh_followers();
                chat_manager.get_messages({model: self.res_model, res_id: self.res_id});
            },
        });
    },
    on_remove_activity: function (event) {
        event.preventDefault();
        var self = this,
            activity_id =  this.$(event.currentTarget).data('activity-id') || false;
        this.remove_activity_log(activity_id)
            .then(function (res) {
                self.fetch_and_render_activity_log();
            });
    },
    on_mark_as_done: function (event) {
        event.preventDefault();
        var self = this,
            activity_id =  this.$(event.currentTarget).data('activity-id') || false;
        this.mark_as_done(activity_id)
            .then(function (msg_id) {
                self.fetch_and_render_activity_log();
                self.chatter.msg_ids.unshift(msg_id);
                // to stop scrollbar flickering add min hedight of the thread and remove after
                // render. on render thread it will remove and add all it's element which cause flickering
                var thread = self.chatter.thread;
                thread.$el.css('min-height', thread.$el.height());
                self.chatter.fetch_and_render_thread(self.chatter.msg_ids).then(function(){
                    thread.$el.css('min-height', '');
                });
            });
    },
    fetch_and_render_activity_log: function () {
        var self = this;
        return self.fetch_activities().then(function (records){
            if (records.length) {
                self.$el.html(QWeb.render('mail.Activity.Log', {
                    activities: records,
                }));
            }
            else {
                self.$el.empty();
            }
        });
    },
    update_activity: function (model, res_id) {
        this.res_model = model;
        this.res_id = res_id;
        this.fetch_and_render_activity_log();
    },
});

// -----------------------------------------------------------------------------
// Kanban widgets: Activity
// -----------------------------------------------------------------------------

var KanbanActivity = AbstractField.extend(AbstractActivityLog, {
    template: 'mail.KanbanActivity',
    events: {
        "click .o_activity_btn": "get_activity_logs",
        "click .o_schedule_activity": "on_open_schedule_activity",
        "click .o_mark_as_done": "on_mark_as_done",
    },
    init: function(parent, field, $node) {
        this._super.apply(this, arguments);
        AbstractActivityLog.init.call(this, parent.id, parent.model);
        this.parent = parent;
        this.activity_state = parent.record.activity_state.raw_value;
        this.selection = _.object(parent.fields.activity_state.selection);
    },
    get_activity_logs: function(event) {
        event.preventDefault();
        var self = this;
        this.$('.o_activity').html(QWeb.render("mail.KanbanActivityLoading"));
        this.fetch_activities()
            .then(function(records) {
                self.$('.o_activity').html($(QWeb.render("mail.KanbanActivityDropdown", {
                    selection: self.selection,
                    records: _.groupBy(records, 'state'),
                    uid: self.session.uid,
                })));
            });
    },
    on_open_schedule_activity: function(event) {
        var self = this,
            activity_id = this.$(event.currentTarget).data('activity-id') || false,
            action = this.get_create_activity_action(activity_id);
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
        this.mark_as_done(activity_id)
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
                var state_color_class =  'o_activity_color_' + (record.activity_state || 'default');
                var current_state_class = 'o_activity_color_' + (self.activity_state || 'default');
                self.$(".o_activity_btn > span").removeClass(current_state_class).addClass(state_color_class);
                self.activity_state = record.activity_state;
                self.parent.record.activity_log_ids.raw_value = record.activity_log_ids;
            });
    }
});
fields_registry.add('kanban_activity', KanbanActivity);

return {
    AbstractActivityLog: AbstractActivityLog,
    ActivityLogList: ActivityLogList,
    KanbanActivity: KanbanActivity
};
});
