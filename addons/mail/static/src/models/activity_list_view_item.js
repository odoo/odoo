/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

import { auto_str_to_date } from 'web.time';
import { sprintf } from '@web/core/utils/strings';

registerModel({
    name: 'ActivityListViewItem',
    recordMethods: {
        onClickEditActivityButton() {
            const popoverViewOwner = this.activityListViewOwner.popoverViewOwner;
            const webRecord = this.webRecord;
            const thread = this.activity.thread;
            this.activity.edit().then(() => {
                webRecord.model.load({ resId: thread.id });
            });
            popoverViewOwner.delete();
        },
        onClickMarkAsDone() {
            this.update({ markDonePopoverView: this.markDonePopoverView ? clear() : {} });
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
         * @param {MouseEvent} ev
         * @returns {Promise}
         */
        async onClickSendMailTemplate(ev, mailTemplateId) {
            await this.messaging.rpc({
                model: this.activity.thread.model,
                method: 'activity_send_mail',
                args: [this.activity.thread.id, mailTemplateId],
            });
            this.activity.thread.fetchData(['activities']);
        },
        onClickPreviewMailTemplate(ev, mailTemplateId) {
            const action = {
                name: this.env._t('Compose Email'),
                type: 'ir.actions.act_window',
                res_model: 'mail.compose.message',
                views: [[false, 'form']],
                target: 'new',
                context: {
                    default_res_id: this.activity.thread.id,
                    default_model: this.activity.thread.model,
                    default_use_template: true,
                    default_template_id: mailTemplateId,
                    force_email: true,
                },
            };
           this.env.services.action.doAction(action, {
                on_close: () => {
                   if (!this.activity.thread.exists()) {
                       return;
                   }
                   this.activity.thread.fetchData(['activities']);
                },
            });
            this.activityListViewOwner.popoverViewOwner.delete();
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
        markDoneButtonRef: attr(),
        markDonePopoverView: one('PopoverView', {
            inverse: 'activityListViewItemOwnerAsMarkDone',
        }),
        webRecord: attr({
            compute() {
                return this.activityListViewOwner.webRecord;
            },
            required: true,
        }),
    },
});
