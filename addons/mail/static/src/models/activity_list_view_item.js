/** @odoo-module **/

import { attr, clear, many, one, Model } from "@mail/model";

import { auto_str_to_date } from "web.time";
import { sprintf } from "@web/core/utils/strings";

Model({
    name: "ActivityListViewItem",
    template: "mail.ActivityListViewItem",
    recordMethods: {
        onClickEditActivityButton() {
            const popoverViewOwner = this.activityListViewOwner.popoverViewOwner;
            const reloadFunc = this.reloadFunc;
            const webRecord = this.webRecord;
            const thread = this.activity.thread;
            this.activity.edit().then(() => {
                if (reloadFunc) {
                    reloadFunc();
                }
                if (webRecord) {
                    webRecord.model.load({ resId: thread.id });
                }
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
        activity: one("Activity", { identifying: true }),
        activityListViewOwner: one("ActivityListView", {
            identifying: true,
            inverse: "activityListViewItems",
        }),
        activityListViewOwnerAsOverdue: one("ActivityListView", {
            inverse: "overdueActivityListViewItems",
            compute() {
                return this.activity.state === "overdue" ? this.activityListViewOwner : clear();
            },
        }),
        activityListViewOwnerAsPlanned: one("ActivityListView", {
            inverse: "plannedActivityListViewItems",
            compute() {
                return this.activity.state === "planned" ? this.activityListViewOwner : clear();
            },
        }),
        activityListViewOwnerAsToday: one("ActivityListView", {
            inverse: "todayActivityListViewItems",
            compute() {
                return this.activity.state === "today" ? this.activityListViewOwner : clear();
            },
        }),
        clockWatcher: one("ClockWatcher", {
            default: { clock: { frequency: 60 * 1000 } },
            inverse: "activityListViewItemOwner",
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
                const today = moment(this.clockWatcher.clock.date.getTime()).startOf("day");
                const momentDeadlineDate = moment(auto_str_to_date(this.activity.dateDeadline));
                // true means no rounding
                const diff = momentDeadlineDate.diff(today, "days", true);
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
        fileUploader: one("FileUploader", {
            inverse: "activityListViewItemOwner",
            compute() {
                return this.activity.category === "upload_file" ? {} : clear();
            },
        }),
        hasEditButton: attr({
            compute() {
                return this.activity.chaining_type === "suggest" && this.activity.canWrite;
            },
        }),
        hasMarkDoneButton: attr({
            compute() {
                return !this.fileUploader;
            },
        }),
        mailTemplateViews: many("MailTemplateView", {
            inverse: "activityListViewItemOwner",
            compute() {
                return this.activity.mailTemplates.map((mailTemplate) => ({ mailTemplate }));
            },
        }),
        markDoneView: one("ActivityMarkDonePopoverContentView", {
            inverse: "activityListViewItemOwner",
        }),
        reloadFunc: attr({
            compute() {
                return this.activityListViewOwner.reloadFunc
                    ? this.activityListViewOwner.reloadFunc
                    : clear();
            },
        }),
        webRecord: attr({
            compute() {
                return this.activityListViewOwner.webRecord
                    ? this.activityListViewOwner.webRecord
                    : clear();
            },
        }),
    },
});
