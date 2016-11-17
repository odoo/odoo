odoo.define('mail.activity.log', function (require) {
"use strict";

var Model = require("web.Model");


var AbstractActivity = {
    init: function(res_id, res_model){
        this.res_id = res_id;
        this.res_model = res_model;
        this.limit = 10;  // TODO Add pager
        this.Activity = new Model("mail.activity");
    },
    remove_activity_log: function (activity_id) {
        return this.Activity.call("unlink", [activity_id]);
    },
    mark_as_done: function (activity_id) {
        return this.Activity.call("mark_as_done", [activity_id]);
    },
    get_create_activity_action : function(activity_id){
        var context = activity_id ? {'mark_done': true} : {}
        return {
            type: 'ir.actions.act_window',
            res_model: 'mail.activity',
            view_mode: 'form',
            view_type: 'form',
            views: [
                [false, 'form']
            ],
            target: 'new',
            context: _.extend({
                default_res_id: this.res_id,
                default_res_model: this.res_model,
            }, context, this.context),
            res_id: activity_id,
        };
    },
};

return {
    AbstractActivity: AbstractActivity,
};
});
