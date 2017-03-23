odoo.define('mail.activity', function (require) {
"use strict";

var core = require('web.core');
var form_common = require('web.form_common');
var Model = require("web.Model");
var ChatManager = require('mail.chat_manager');
var QWeb = core.qweb;
var time = require('web.time');
var _t = core._t;


/**
 * Set the 'label_delay' entry in activity data according to the deadline date
 * @param {Array} list of activity Object
 * @return {Array} : list of modified activity Object
 */
var set_delay_label = function(activities){
    var today = moment().startOf('day');
    _.each(activities, function(activity){
        var to_display = '';
        var deadline = moment(activity.date_deadline + ' 00:00:00');
        var diff = deadline.diff(today, 'days', true); // true means no rounding
        if(diff === 0){
            to_display = _t('Today');
        }else{
            if(diff < 0){ // overdue
                if(diff === -1){
                    to_display = _t('Yesterday');
                }else{
                    to_display = _.str.sprintf(_t('%d days overdue'), Math.abs(diff));
                }
            }else{ // due
                if(diff === 1){
                    to_display = _t('Tomorrow');
                }else{
                    to_display = _.str.sprintf(_t('Due in %d days'), Math.abs(diff));
                }
            }
        }
        activity['label_delay'] = to_display;
    });
    return activities;
};

// -----------------------------------------------------------------------------
// Activities Widget ('mail_activity' widget)
//
// Since it is displayed on a form view, it extends 'AbstractField' widget.
//
// Note: the activity widget is moved inside the chatter by the chatter itself
// for layout purposes.
// -----------------------------------------------------------------------------

var Activity = form_common.AbstractField.extend({
    className: 'o_mail_activity',

    events: {
        "click .o_activity_edit": "on_activity_edit",
        "click .o_activity_unlink": "on_activity_unlink",
        "click .o_activity_done": "on_activity_done",
    },

    init: function () {
        this._super.apply(this, arguments);

        this.context = this.options.context || {};
        this.model = this.view.dataset.model;
        this.activities = [];
        this.Activity = new Model('mail.activity');
    },

    start: function () {
        // Hide the chatter in 'create' mode
        this.view.on("change:actual_mode", this, this.check_visibility);

        // find chatter if any
        this.chatter = this.field_manager.fields.message_ids;

        return this._super();
    },

    get_res_id: function () {
        return this.view.datarecord.id;
    },

    check_visibility: function () {
        this.set({"force_invisible": this.view.get("actual_mode") === "create"});
    },

    set_value: function (_value) {
        this.value = _value;
        this._super(_value);
    },

    fetch_and_render_value: function () {
        var self = this;

        return new Model(this.model)
            .call("read", [[this.get_res_id()], ['activity_ids']])
            .then(function (results) {
                self.value = results[0]['activity_ids'];
                return self.render_value();
            });
    },

    render_value: function () {
        var self = this;

        return this.Activity
            .call("read", [this.value])
            .then(function (results) {
                _.each(results, function(result){
                    result['time_ago'] = moment(time.auto_str_to_date(result.create_date)).fromNow();
                });
                this.activities = set_delay_label(results);
                self.$el.html(QWeb.render('mail.activity_items', {
                    activities: this.activities,
                }));
            });
    },

    on_activity_schedule: function (event) {
        event.preventDefault();
        var self = this;
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
                default_res_id: this.get_res_id(),
                default_res_model: this.model,
            }, {'mark_done': true}, this.context),
            res_id: false,
        };
        return this.do_action(action, {
            on_close: function() {
                self.fetch_and_render_value();
                self.chatter.refresh_followers();
                ChatManager.get_messages({model: self.model, res_id: self.get_res_id()});
            },
        });
    },

    on_activity_edit: function (event) {
        event.preventDefault();
        var self = this;
        var activity_id = this.$(event.currentTarget).data('activity-id');
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
                default_res_id: this.get_res_id(),
                default_res_model: this.model,
            }, {'mark_done': true}, this.context),
            res_id: activity_id,
        };
        this.do_action(action, {
            on_close: function () {
                self.fetch_and_render_value();
                self.chatter.refresh_followers();
                ChatManager.get_messages({model: self.model, res_id: self.get_res_id()});
            },
        });
    },

    on_activity_unlink: function (event) {
        event.preventDefault();
        var self = this;
        var activity_id = this.$(event.currentTarget).data('activity-id');
        this.Activity
            .call("unlink", [[activity_id]])
            .then(function () {
                self.fetch_and_render_value();
            });
    },

    on_activity_done: function (event) {
        event.preventDefault();
        var self = this;
        var activity_id = this.$(event.currentTarget).data('activity-id');
        this.Activity
            .call("action_done", [[activity_id]])
            .then(function (msg_id) {
                self.fetch_and_render_value();

                self.chatter.msg_ids.unshift(msg_id);

                // to stop scrollbar flickering add min height of the thread and remove after
                // render. on render thread it will remove and add all it's element which cause flickering
                var thread = self.chatter.thread;
                thread.$el.css('min-height', thread.$el.height());
                self.chatter.fetch_and_render_thread(self.chatter.msg_ids).then(function () {
                    thread.$el.css('min-height', '');
                });

            });
    },
});

core.form_widget_registry.add('mail_activity', Activity);

return {
    Activity: Activity,
    set_delay_label: set_delay_label,
};

});
