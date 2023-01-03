/** @odoo-module **/

import { attr, clear, many, one, Model } from "@mail/model";

import session from "web.session";

Model({
    name: "ActivityListView",
    template: "mail.ActivityListView",
    lifecycleHooks: {
        async _created() {
            if (this.activities.length === 0) {
                return;
            }
            const messaging = this.messaging;
            const activitiesData = await this.messaging.rpc(
                {
                    model: "mail.activity",
                    method: "activity_format",
                    args: [this.activities.map((activity) => activity.id)],
                    kwargs: { context: session.user_context },
                },
                { shadow: true }
            );
            if (!messaging.exists()) {
                return;
            }
            messaging.models["Activity"].insert(
                activitiesData.map((activityData) =>
                    messaging.models["Activity"].convertData(activityData)
                )
            );
        },
    },
    recordMethods: {
        onClickAddActivityButton() {
            const reloadFunc = this.reloadFunc;
            const thread = this.thread;
            const webRecord = this.webRecord;
            this.messaging
                .openActivityForm({
                    defaultActivityTypeId: this.popoverViewOwner.activityCellViewOwnerAsActivityList
                        ? this.popoverViewOwner.activityCellViewOwnerAsActivityList.activityType.id
                        : undefined,
                    thread,
                })
                .then(() => {
                    thread.fetchData(["activities"]);
                    if (reloadFunc) {
                        reloadFunc();
                    }
                    if (webRecord) {
                        webRecord.model.load({ resId: thread.id });
                    }
                });
            this.popoverViewOwner.delete();
        },
    },
    fields: {
        activities: many("Activity", {
            compute() {
                if (this.popoverViewOwner.activityCellViewOwnerAsActivityList) {
                    return this.popoverViewOwner.activityCellViewOwnerAsActivityList
                        .filteredActivities;
                }
                return this.thread && this.thread.activities;
            },
            sort: [
                ["truthy-first", "dateDeadline"],
                ["case-insensitive-asc", "dateDeadline"],
            ],
        }),
        activityListViewItems: many("ActivityListViewItem", {
            inverse: "activityListViewOwner",
            compute() {
                return this.activities.map((activity) => {
                    return {
                        activity,
                    };
                });
            },
        }),
        overdueActivityListViewItems: many("ActivityListViewItem", {
            inverse: "activityListViewOwnerAsOverdue",
        }),
        plannedActivityListViewItems: many("ActivityListViewItem", {
            inverse: "activityListViewOwnerAsPlanned",
        }),
        popoverViewOwner: one("PopoverView", { identifying: true, inverse: "activityListView" }),
        reloadFunc: attr({
            compute() {
                return this.popoverViewOwner.activityCellViewOwnerAsActivityList
                    ? this.popoverViewOwner.activityCellViewOwnerAsActivityList.reloadFunc
                    : clear();
            },
        }),
        thread: one("Thread", {
            required: true,
            compute() {
                if (this.popoverViewOwner.activityButtonViewOwnerAsActivityList) {
                    return this.popoverViewOwner.activityButtonViewOwnerAsActivityList.thread;
                }
                if (this.popoverViewOwner.activityCellViewOwnerAsActivityList) {
                    return this.popoverViewOwner.activityCellViewOwnerAsActivityList.thread;
                }
                return clear();
            },
        }),
        todayActivityListViewItems: many("ActivityListViewItem", {
            inverse: "activityListViewOwnerAsToday",
        }),
        webRecord: attr({
            compute() {
                if (this.popoverViewOwner.activityButtonViewOwnerAsActivityList) {
                    return this.popoverViewOwner.activityButtonViewOwnerAsActivityList.webRecord;
                }
                return clear();
            },
        }),
    },
});
