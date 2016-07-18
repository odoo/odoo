odoo.define('mail.ActivityLog', function (require) {
"use strict";

var core = require('web.core');
var Model = require("web.Model");
var Widget = require('web.Widget');

var QWeb = core.qweb;

// -----------------------------------------------------------------------------
// Activity Log
//
// Integrated with Chatter
// -----------------------------------------------------------------------------
var ActivityLog = Widget.extend({
    template: "mail.Activity",
    init: function (res_id, model) {
        this._super.apply(this, arguments);
        this.model = model;
        this.res_id = res_id;
        this.limit = 10;  // TODO Add pager
        this.ActivityLogModel = new Model("mail.activity.log");
    },
    start: function () {
        this.fetch_and_render_activity_log();
    },
    fetch_activities: function () {
        return this.ActivityLogModel
            .call("fetch_activity_logs", [this.res_id, this.model, this.limit || false]);
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
    add_activity_action : function(activity_id){
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
                default_model: this.model,
            }, this.context),
            res_id: activity_id,
        };
    },
    update_activity: function (model, res_id) {
        this.model = model;
        this.res_id = res_id;
        this.fetch_and_render_activity_log();
    },
    remove_activity_log: function (activity_id) {
        return this.ActivityLogModel.call("remove_activity_log", [activity_id]);
    },
    mark_as_done: function (activity_id) {
        return this.ActivityLogModel.call("mark_as_done", [activity_id]);
    },
});

return ActivityLog;
});
