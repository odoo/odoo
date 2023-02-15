/** @odoo-module **/

import { attr, clear, many, one, Model } from "@mail/model";

import { auto_str_to_date, getLangDateFormat, getLangDatetimeFormat } from "web.time";
import { sprintf } from "@web/core/utils/strings";

Model({
    name: "ActivityView",
    template: "mail.ActivityView",
    recordMethods: {
        /**
         * Handles the click on a link inside the activity.
         *
         * @param {MouseEvent} ev
         */
        onClickActivity(ev) {
            if (ev.target.tagName === "A" && ev.target.dataset.oeId && ev.target.dataset.oeModel) {
                this.messaging.openProfile({
                    id: Number(ev.target.dataset.oeId),
                    model: ev.target.dataset.oeModel,
                });
                // avoid following dummy href
                ev.preventDefault();
            }
        },
        /**
         * Handles the click on the cancel button
         */
        async onClickCancel() {
            const chatter = this.chatterOwner; // save value before deleting activity
            await this.activity.deleteServerRecord();
            if (chatter.exists() && chatter.component) {
                chatter.reloadParentView();
            }
        },
        /**
         * Handles the click on the detail button
         */
        onClickDetailsButton(ev) {
            ev.preventDefault();
            this.update({ areDetailsVisible: !this.areDetailsVisible });
        },
        /**
         * Handles the click on the edit button
         */
        async onClickEdit() {
            const chatter = this.chatterOwner;
            await this.activity.edit();
            if (chatter.exists() && chatter.component) {
                chatter.reloadParentView();
            }
        },
        onClickMarkDoneButton() {
            this.update({ markDonePopoverView: this.markDonePopoverView ? clear() : {} });
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
        activity: one("Activity", { identifying: true, inverse: "activityViews" }),
        /**
         * Determines whether the details are visible.
         */
        areDetailsVisible: attr({ default: false }),
        /**
         * Compute the string for the assigned user.
         */
        assignedUserText: attr({
            compute() {
                if (!this.activity.assignee) {
                    return clear();
                }
                return sprintf(this.env._t("for %s"), this.activity.assignee.nameOrDisplayName);
            },
        }),
        chatterOwner: one("Chatter", { identifying: true, inverse: "activityViews" }),
        clockWatcher: one("ClockWatcher", {
            default: { clock: { frequency: 60 * 1000 } },
            inverse: "activityViewOwner",
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
                    return this.env._t("Today:");
                } else if (diff === -1) {
                    return this.env._t("Yesterday:");
                } else if (diff < 0) {
                    return sprintf(this.env._t("%s days overdue:"), Math.round(Math.abs(diff)));
                } else if (diff === 1) {
                    return this.env._t("Tomorrow:");
                } else {
                    return sprintf(this.env._t("Due in %s days:"), Math.round(Math.abs(diff)));
                }
            },
        }),
        fileUploader: one("FileUploader", {
            inverse: "activityView",
            compute() {
                return this.activity.category === "upload_file" ? {} : clear();
            },
        }),
        /**
         * Format the create date to something human reabable.
         */
        formattedCreateDatetime: attr({
            compute() {
                if (!this.activity.dateCreate) {
                    return clear();
                }
                const momentCreateDate = moment(auto_str_to_date(this.activity.dateCreate));
                const datetimeFormat = getLangDatetimeFormat();
                return momentCreateDate.format(datetimeFormat);
            },
        }),
        /**
         * Format the deadline date to something human reabable.
         */
        formattedDeadlineDate: attr({
            compute() {
                if (!this.activity.dateDeadline) {
                    return clear();
                }
                const momentDeadlineDate = moment(auto_str_to_date(this.activity.dateDeadline));
                const datetimeFormat = getLangDateFormat();
                return momentDeadlineDate.format(datetimeFormat);
            },
        }),
        mailTemplateViews: many("MailTemplateView", {
            inverse: "activityViewOwner",
            compute() {
                return this.activity.mailTemplates.map((mailTemplate) => ({ mailTemplate }));
            },
        }),
        markDoneButtonRef: attr({ ref: "markDoneButton" }),
        markDonePopoverView: one("PopoverView", { inverse: "activityViewOwnerAsMarkDone" }),
        /**
         * Label for mark as done. This is just for translations purpose.
         */
        markDoneText: attr({
            compute() {
                return this.env._t("Mark Done");
            },
        }),
        /**
         * Format the summary.
         */
        summary: attr({
            compute() {
                if (!this.activity.summary) {
                    return clear();
                }
                return sprintf(this.env._t("“%s”"), this.activity.summary);
            },
        }),
    },
});
