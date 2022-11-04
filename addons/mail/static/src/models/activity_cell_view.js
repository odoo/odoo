/** @odoo-module **/

import { attr, clear, many, one, registerModel } from '@mail/model';

registerModel({
    name: 'ActivityCellView',
    recordMethods: {
        onClick() {
            this.update({ activityListPopoverView: this.activityListPopoverView ? clear() : {} });
        },
    },
    fields: {
        activityListPopoverView: one('PopoverView', { inverse: 'activityCellViewOwnerAsActivityList' }),
        activityType: one('ActivityType', { required: true }),
        closestDeadline: attr({ required: true }),
        closestDeadlineFormatted: attr({
            compute() {
                const date = moment(this.closestDeadline).toDate();
                // To remove year only if current year
                if (moment().year() === moment(date).year()) {
                    return date.toLocaleDateString(moment().locale(), {
                        day: 'numeric', month: 'short'
                    });
                } else {
                    return moment(date).format('ll');
                }
            },
        }),
        contentRef: attr(),
        filteredActivities: many('Activity', {
            compute() {
                return this.thread.activities.filter(activity => activity.type === this.activityType);
            },
        }),
        id: attr({ identifying: true }),
        reloadFunc: attr({ required: true }),
        thread: one('Thread', { required: true }),
    },
});
