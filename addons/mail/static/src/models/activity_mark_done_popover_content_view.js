/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'ActivityMarkDonePopoverContentView',
    recordMethods: {
        /**
         * Handles blur on this feedback textarea.
         */
        onBlur() {
            if (!this.exists() || !this.feedbackTextareaRef || !this.feedbackTextareaRef.el) {
                return;
            }
            this._backupFeedback();
        },
        /**
         * Handles click on this "Discard" button.
         */
        onClickDiscard() {
            this._close();
        },
        /**
         * Handles click on this "Done" button.
         */
        async onClickDone() {
            const chatter = this.activityViewOwner && this.activityViewOwner.activityBoxView.chatter;
            const webRecord = this.webRecord;
            const thread = this.activity.thread;
            await this.activity.markAsDone({
                feedback: this.feedbackTextareaRef.el.value,
            });
            if (chatter && chatter.exists() && chatter.component) {
                chatter.reloadParentView();
            }
            if (webRecord) {
                webRecord.model.load({ resId: thread.id });
            }
        },
        /**
         * Handles click on this "Done & Schedule Next" button.
         */
        async onClickDoneAndScheduleNext() {
            const chatter = this.activityViewOwner && this.activityViewOwner.activityBoxView.chatter;
            const webRecord = this.webRecord;
            const thread = this.activity.thread;
            const activityListViewOwner = this.activityListViewItemOwner && this.activityListViewItemOwner.activityListViewOwner;
            await this.activity.markAsDoneAndScheduleNext({
                feedback: this.feedbackTextareaRef.el.value,
            });
            if (chatter && chatter.exists() && chatter.component) {
                chatter.reloadParentView();
            }
            if (webRecord) {
                webRecord.model.load({ resId: thread.id });
            }
            if (activityListViewOwner && activityListViewOwner.exists()) {
                activityListViewOwner.popoverViewOwner.delete();
            }
        },
        /**
         * Handles keydown on this activity mark done.
         */
        onKeydown(ev) {
            if (ev.key === 'Escape') {
                this._close();
            }
        },
        /**
         * @private
         */
        _backupFeedback() {
            this.activity.update({
                feedbackBackup: this.feedbackTextareaRef.el.value,
            });
        },
        /**
         * @private
         */
        _close() {
            this._backupFeedback();
            if (this.activityViewOwner) {
                this.activityViewOwner.update({ markDonePopoverView: clear() });
                return;
            }
            if (this.activityListViewItemOwner) {
                this.activityListViewItemOwner.markDonePopoverView.delete();
                return;
            }
        },
    },
    fields: {
        activity: one('Activity', {
            compute() {
                if (this.activityListViewItemOwner) {
                    return this.activityListViewItemOwner.activity;
                }
                if (this.activityViewOwner) {
                    return this.activityViewOwner.activity;
                }
                return clear();
            },
            required: true,
        }),
        activityListViewItemOwner: one('ActivityListViewItem', {
            compute() {
                if (this.popoverViewOwner.activityListViewItemOwnerAsMarkDone) {
                    return this.popoverViewOwner.activityListViewItemOwnerAsMarkDone;
                }
                return clear();
            },
        }),
        activityViewOwner: one('ActivityView', {
            compute() {
                if (this.popoverViewOwner.activityViewOwnerAsMarkDone) {
                    return this.popoverViewOwner.activityViewOwnerAsMarkDone;
                }
                return clear();
            },
        }),
        component: attr(),
        feedbackTextareaRef: attr(),
        headerText: attr({
            compute() {
                if (this.activityViewOwner) {
                    return this.activityViewOwner.markDoneText;
                }
                return this.env._t("Mark Done");
            },
        }),
        popoverViewOwner: one('PopoverView', {
            identifying: true,
            inverse: 'activityMarkDonePopoverContentView',
        }),
        webRecord: attr({
            compute() {
                if (this.activityListViewItemOwner) {
                    return this.activityListViewItemOwner.webRecord;
                }
                return clear();
            },
        }),
    },
});
