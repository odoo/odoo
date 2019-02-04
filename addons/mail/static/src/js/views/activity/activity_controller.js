odoo.define('mail.ActivityController', function (require) {
"use strict";

var BasicController = require('web.BasicController');

var ActivityController = BasicController.extend({
    custom_events: _.extend({}, BasicController.prototype.custom_events, {
        send_mail_template: '_onSendMailTemplate',
    }),

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Overridden to remove the pager as it makes no sense in this view.
     *
     * @override
     */
    renderPager: function () {
        return Promise.resolve();
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onSendMailTemplate: function (ev) {
        var templateID = ev.data.templateID;
        var activityTypeID = ev.data.activityTypeID;
        var state = this.model.get(this.handle);
        var groupedActivities = state.grouped_activities;
        var resIDS = [];
        Object.keys(groupedActivities).forEach(function (resID) {
            var activityByType = groupedActivities[resID];
            var activity = activityByType[activityTypeID];
            if (activity) {
                resIDS.push(parseInt(resID));
            }
        });
        this._rpc({
            model: this.model.modelName,
            method: 'activity_send_mail',
            args: [resIDS, templateID],
        });
    },
});

return ActivityController;

});
