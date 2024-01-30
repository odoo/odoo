/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

import { auto_str_to_date } from 'web.time';
import { sprintf } from '@web/core/utils/strings';

registerModel({
    name: 'ActivityListViewItem',
    recordMethods: {
        onClickEditActivityButton() {
            const popoverViewOwner = this.activityListViewOwner.popoverViewOwner;
            const webRecord = this.webRecord;
            this.activity.edit().then(() => {
                webRecord.model.load({ offset: webRecord.model.root.offset });
            });
            popoverViewOwner.delete();
        },
        onClickMarkAsDone() {
            this.update({ markDoneView: this.markDoneView ? clear() : {} });
        },
        /**
         * Handles the click on the upload document button. This open the file
         * explorer for upload.
         */
        onClickUploadDocument() {
            this.fileUploader.openBrowserFileUploader();
        },
    },
    fields: {
        activity: one('Activity', {
            identifying: true,
        }),
        activityListViewOwner: one('ActivityListView', {
            identifying: true,
            inverse: 'activityListViewItems',
        }),
        activityListViewOwnerAsOverdue: one('ActivityListView', {
            compute() {
                return this.activity.state === 'overdue' ? this.activityListViewOwner : clear();
            },
            inverse: 'overdueActivityListViewItems',
        }),
        activityListViewOwnerAsPlanned: one('ActivityListView', {
            compute() {
                return this.activity.state === 'planned' ? this.activityListViewOwner : clear();
            },
            inverse: 'plannedActivityListViewItems',
        }),
        activityListViewOwnerAsToday: one('ActivityListView', {
            compute() {
                return this.activity.state === 'today' ? this.activityListViewOwner : clear();
            },
            inverse: 'todayActivityListViewItems',
        }),
        clockWatcher: one('ClockWatcher', {
            default: {
                clock: {
                    frequency: 60 * 1000,
                },
            },
            inverse: 'activityListViewItemOwner',
        }),
        /**
         * Compute the label for "when" the activity is due.
         */
        delayLabel: attr({
            compute() {
                if (!this.activity.dateDeadline) {
                    return clear();
                }
                if (!this.clockWatcher.clock.date) {
                    return clear();
                }
                const today = moment(this.clockWatcher.clock.date.getTime()).startOf('day');
                const momentDeadlineDate = moment(auto_str_to_date(this.activity.dateDeadline));
                // true means no rounding
                const diff = momentDeadlineDate.diff(today, 'days', true);
                if (diff === 0) {
                    return this.env._t("Today");
                } else if (diff === -1) {
                    return this.env._t("Yesterday");
                } else if (diff < 0) {
                    return sprintf(this.env._t("%s days overdue"), Math.round(Math.abs(diff)));
                } else if (diff === 1) {
                    return this.env._t("Tomorrow");
                } else {
                    return sprintf(this.env._t("Due in %s days"), Math.round(Math.abs(diff)));
                }
            },
        }),
        fileUploader: one('FileUploader', {
            compute() {
                return this.activity.category === 'upload_file' ? {} : clear();
            },
            inverse: 'activityListViewItemOwner',
        }),
        hasEditButton: attr({
            compute() {
                return this.activity.chaining_type === 'suggest' && this.activity.canWrite;
            },
        }),
        hasMarkDoneButton: attr({
            compute() {
                return !this.fileUploader;
            },
        }),
        mailTemplateViews: many('MailTemplateView', {
            compute() {
                return this.activity.mailTemplates.map(mailTemplate => ({ mailTemplate }));
            },
            inverse: 'activityListViewItemOwner',
        }),
        markDoneView: one('ActivityMarkDonePopoverContentView', {
            inverse: 'activityListViewItemOwner',
        }),
        webRecord: attr({
            compute() {
                return this.activityListViewOwner.webRecord;
            },
            required: true,
        }),
    },
});
