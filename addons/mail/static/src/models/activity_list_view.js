/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';

import session from 'web.session';

registerModel({
    name: 'ActivityListView',
    lifecycleHooks: {
        async _created() {
            if (this.activities.length === 0) {
                return;
            }
            const messaging = this.messaging;
            const activitiesData = await this.messaging.rpc({
                model: 'mail.activity',
                method: 'activity_format',
                args: [this.activities.map(activity => activity.id)],
                kwargs: { context: session.user_context },
            }, { shadow: true });
            if (!messaging.exists()) {
                return;
            }
            messaging.models['Activity'].insert(
                activitiesData.map(activityData => messaging.models['Activity'].convertData(activityData))
            );
        },
    },
    recordMethods: {
        onClickAddActivityButton() {
            const thread = this.thread;
            const webRecord = this.webRecord;
            this.messaging.openActivityForm({
                thread,
            }).then(() => {
                thread.fetchData(['activities']);
                webRecord.model.load({ resId: thread.id });
            });
            this.popoverViewOwner.delete();
        },
    },
    fields: {
        activities: many('Activity', {
            compute() {
                return this.thread && this.thread.activities;
            },
            sort: [
                ['truthy-first', 'dateDeadline'],
                ['case-insensitive-asc', 'dateDeadline'],
            ],
        }),
        activityListViewItems: many('ActivityListViewItem', {
            compute() {
                return this.activities.map(activity => {
                    return {
                        activity,
                    };
                });
            },
            inverse: 'activityListViewOwner',
        }),
        overdueActivityListViewItems: many('ActivityListViewItem', {
            inverse: 'activityListViewOwnerAsOverdue',
        }),
        plannedActivityListViewItems: many('ActivityListViewItem', {
            inverse: 'activityListViewOwnerAsPlanned',
        }),
        popoverViewOwner: one('PopoverView', {
            identifying: true,
            inverse: 'activityListView',
        }),
        thread: one('Thread', {
            compute() {
                return this.popoverViewOwner.activityButtonViewOwnerAsActivityList.thread;
            },
            required: true,
        }),
        todayActivityListViewItems: many('ActivityListViewItem', {
            inverse: 'activityListViewOwnerAsToday',
        }),
        webRecord: attr({
            compute() {
                return this.popoverViewOwner.activityButtonViewOwnerAsActivityList.webRecord;
            },
            required: true,
        }),
    },
});
