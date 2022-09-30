/** @odoo-module **/

import '@mail/js/activity';

import BasicController from 'web.BasicController';
import core from 'web.core';
import { sprintf } from '@web/core/utils/strings';

import { SelectCreateDialog } from '@web/views/view_dialogs/select_create_dialog';

const { Component } = owl;
var _t = core._t;

var ActivityController = BasicController.extend({
    custom_events: _.extend({}, BasicController.prototype.custom_events, {
        empty_cell_clicked: '_onEmptyCell',
        send_mail_template: '_onSendMailTemplate',
        schedule_activity: '_onScheduleActivity',
    }),

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     * @param parent
     * @param model
     * @param renderer
     * @param {Object} params
     * @param {String} params.title The title used in schedule activity dialog
     */
    init: function (parent, model, renderer, params) {
        this._super.apply(this, arguments);
        this.title = params.title;
        this.searchViewId = params.searchViewId;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Overridden to remove the pager as it makes no sense in this view.
     *
     * @override
     */
    _getPagingInfo: function () {
        return null;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onScheduleActivity: function () {
        var state = this.model.get(this.handle);
        Component.env.services.dialog.add(SelectCreateDialog, {
            resModel: state.model,
            searchViewId: this.searchViewId,
            domain: this.model.originalDomain,
            title: sprintf(_t("Search: %s"), this.title),
            noCreate: !this.activeActions.create,
            multiSelect: false,
            context: state.context,
            onSelected: async resIds => {
                const messaging = await owl.Component.env.services.messaging.get();
                const thread = messaging.models['Thread'].insert({ id: resIds[0], model: this.model.modelName });
                await messaging.openActivityForm({ thread });
                this.trigger_up('reload');
            },
        });
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onEmptyCell: function (ev) {
        var state = this.model.get(this.handle);
        this.do_action({
            type: 'ir.actions.act_window',
            res_model: 'mail.activity',
            view_mode: 'form',
            view_type: 'form',
            views: [[false, 'form']],
            target: 'new',
            context: {
                default_res_id: ev.data.resId,
                default_res_model: state.model,
                default_activity_type_id: ev.data.activityTypeId,
            },
            res_id: false,
        }, {
            on_close: this.reload.bind(this),
        });
    },
    /**
     * @private
     * @param {CustomEvent} ev
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

export default ActivityController;
