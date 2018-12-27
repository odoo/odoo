odoo.define('mail.ActivityController', function (require) {
"use strict";

var AbstractController = require('web.AbstractController');

var ActivityController = AbstractController.extend({
    custom_events: _.extend({}, AbstractController.prototype.custom_events, {
        send_mail_template: '_onSendMailTemplate',
        open_view_form: '_onOpenViewForm',
        reload: '_onReload',
    }),

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {OdooEvent} event
     * @param {string} event.name
     * @param {Object} event.data
     * @param {boolean} [event.data.activity]
     * @param {boolean} [event.data.followers]
     * @param {boolean} [event.data.thread]
     */
    _onReload: function (event) {
        event.stopPropagation();
        var self = this;
        this.model.reload().then(self.reload());
    },

    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onSendMailTemplate: function (ev) {
        var templateID = ev.data.templateID;
        var activityTypeID = ev.data.activityTypeID;
        var state = this.model.get();
        var groupedActivities = state.data.grouped_activities;
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
    /**
    * @private
    * @override
    * @param {MouseEvent} ev
    */
    _onOpenViewForm: function (ev) {
        var resID = ev.data.resID;
        this.do_action({
            type: 'ir.actions.act_window',
            res_model: this.model.modelName,
            res_id: resID,
            views: [[false, 'form']],
            target: 'current'
        });
    },
});

return ActivityController;

});
