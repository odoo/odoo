odoo.define('website_slides.Activity', function (require) {
"use strict";

var field_registry = require('web.field_registry');

require('mail.Activity');

var KanbanActivity = field_registry.get('kanban_activity');

function applyInclude(Activity) {
    Activity.include({
        events: _.extend({}, Activity.prototype.events, {
            'click .o_activity_action_grant_access': '_onGrantAccess',
            'click .o_activity_action_refuse_access': '_onRefuseAccess',
        }),

        _onGrantAccess: function (event) {
            var self = this;
            var partnerId = $(event.currentTarget).data('partner-id');
            this._rpc({
                model: 'slide.channel',
                method: 'action_grant_access',
                args: [this.res_id, partnerId],
            }).then(function (result) {
                self.trigger_up('reload');
            });
        },

        _onRefuseAccess: function (event) {
            var self = this;
            var partnerId = $(event.currentTarget).data('partner-id');
            this._rpc({
                model: 'slide.channel',
                method: 'action_refuse_access',
                args: [this.res_id, partnerId],
            }).then(function () {
                self.trigger_up('reload');
            });
        },
    });
}

applyInclude(KanbanActivity);

});