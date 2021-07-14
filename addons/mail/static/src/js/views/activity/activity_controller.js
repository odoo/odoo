/** @odoo-module **/

import '@mail/js/activity';

import BasicController from 'web.BasicController';
import core from 'web.core';
import field_registry from 'web.field_registry';
import ViewDialogs from 'web.view_dialogs';

var KanbanActivity = field_registry.get('kanban_activity');
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
        var self = this;
        var state = this.model.get(this.handle);
        new ViewDialogs.SelectCreateDialog(this, {
            res_model: state.model,
            searchViewId: this.searchViewId,
            domain: this.model.originalDomain,
            title: _.str.sprintf(_t("Search: %s"), this.title),
            no_create: !this.activeActions.create,
            disable_multiple_selection: true,
            context: state.context,
            on_selected: function (record) {
                var fakeRecord = state.getKanbanActivityData({}, record[0]);
                var widget = new KanbanActivity(self, 'activity_ids', fakeRecord, {});
                widget.scheduleActivity();
            },
        }).open();
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
