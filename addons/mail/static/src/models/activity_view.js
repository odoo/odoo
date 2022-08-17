/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear, insertAndReplace } from '@mail/model/model_field_command';

import { auto_str_to_date, getLangDateFormat, getLangDatetimeFormat } from 'web.time';
import { sprintf } from '@web/core/utils/strings';

registerModel({
    name: 'ActivityView',
    recordMethods: {
        /**
         * Handles the click on a link inside the activity.
         *
         * @param {MouseEvent} ev
         */
        onClickActivity(ev) {
            if (
                ev.target.tagName === 'A' &&
                ev.target.dataset.oeId &&
                ev.target.dataset.oeModel
            ) {
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
            const { chatter } = this.activityBoxView; // save value before deleting activity
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
            const { chatter } = this.activityBoxView;
            await this.activity.edit();
            if (chatter.exists() && chatter.component) {
                chatter.reloadParentView();
            }
        },
        onClickMarkDoneButton() {
            this.update({ markDonePopoverView: this.markDonePopoverView ? clear() : insertAndReplace() });
        },
        /**
         * Handles the click on the upload document button. This open the file
         * explorer for upload.
         */
        onClickUploadDocument() {
            this.fileUploader.openBrowserFileUploader();
        },
        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computeAssignedUserText() {
            if (!this.activity.assignee) {
                return clear();
            }
            return sprintf(this.env._t("for %s"), this.activity.assignee.nameOrDisplayName);
        },
        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computeDelayLabel() {
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
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeFileUploader() {
            return this.activity.category === 'upload_file' ? insertAndReplace() : clear();
        },
        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computeFormattedCreateDatetime() {
            if (!this.activity.dateCreate) {
                return clear();
            }
            const momentCreateDate = moment(auto_str_to_date(this.activity.dateCreate));
            const datetimeFormat = getLangDatetimeFormat();
            return momentCreateDate.format(datetimeFormat);
        },
        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computeFormattedDeadlineDate() {
            if (!this.activity.dateDeadline) {
                return clear();
            }
            const momentDeadlineDate = moment(auto_str_to_date(this.activity.dateDeadline));
            const datetimeFormat = getLangDateFormat();
            return momentDeadlineDate.format(datetimeFormat);
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeMailTemplateViews() {
            if (this.activity.mailTemplates.length === 0) {
                return clear();
            }
            return insertAndReplace(
                this.activity.mailTemplates.map(
                    mailTemplate => ({ mailTemplate })
                ),
            );
        },
        /**
         * @private
         * @returns {string}
         */
        _computeMarkDoneText() {
            return this.env._t("Mark Done");
        },
        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computeSummary() {
            if (!this.activity.summary) {
                return clear();
            }
            return sprintf(this.env._t("“%s”"), this.activity.summary);
        },
    },
    fields: {
        activity: one('Activity', {
            identifying: true,
            inverse: 'activityViews',
        }),
        activityBoxView: one('ActivityBoxView', {
            identifying: true,
            inverse: 'activityViews',
        }),
        /**
         * Determines whether the details are visible.
         */
        areDetailsVisible: attr({
            default: false,
        }),
        /**
         * Compute the string for the assigned user.
         */
        assignedUserText: attr({
            compute: '_computeAssignedUserText',
        }),
        clockWatcher: one('ClockWatcher', {
            default: insertAndReplace({
                clock: insertAndReplace({
                    frequency: 60 * 1000,
                }),
            }),
            inverse: 'activityViewOwner',
            isCausal: true,
        }),
        /**
         * States the OWL component of this activity view.
         */
        component: attr(),
        /**
         * Compute the label for "when" the activity is due.
         */
        delayLabel: attr({
            compute: '_computeDelayLabel',
        }),
        fileUploader: one('FileUploader', {
            compute: '_computeFileUploader',
            inverse: 'activityView',
            isCausal: true,
        }),
        /**
         * Format the create date to something human reabable.
         */
        formattedCreateDatetime: attr({
            compute: '_computeFormattedCreateDatetime',
        }),
        /**
         * Format the deadline date to something human reabable.
         */
        formattedDeadlineDate: attr({
            compute: '_computeFormattedDeadlineDate',
        }),
        mailTemplateViews: many('MailTemplateView', {
            compute: '_computeMailTemplateViews',
            inverse: 'activityViewOwner',
            isCausal: true,
        }),
        markDoneButtonRef: attr(),
        markDonePopoverView: one('PopoverView', {
            inverse: 'activityViewOwnerAsMarkDone',
            isCausal: true,
        }),
        /**
         * Label for mark as done. This is just for translations purpose.
         */
        markDoneText: attr({
            compute: '_computeMarkDoneText',
        }),
        /**
         * Format the summary.
         */
        summary: attr({
            compute: '_computeSummary',
        }),
    },
});
