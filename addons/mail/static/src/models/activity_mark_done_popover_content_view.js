/** @odoo-module **/

import { attr, clear, one, Model } from "@mail/model";

import { onMounted } from "@odoo/owl";

Model({
    name: "ActivityMarkDonePopoverContentView",
    template: "mail.ActivityMarkDonePopoverContentView",
    componentSetup() {
        onMounted(this.onMounted);
    },
    identifyingMode: "xor",
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
        onMounted() {
            this.feedbackTextareaRef.el.focus();
            if (this.activity.feedbackBackup) {
                this.feedbackTextareaRef.el.value = this.activity.feedbackBackup;
            }
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
            const chatter = this.activityViewOwner && this.activityViewOwner.chatterOwner;
            const reloadFunc = this.reloadFunc;
            const webRecord = this.webRecord;
            const thread = this.activity.thread;
            await this.activity.markAsDone({
                feedback: this.feedbackTextareaRef.el.value,
            });
            if (chatter && chatter.exists() && chatter.component) {
                chatter.reloadParentView();
            }
            if (reloadFunc) {
                reloadFunc();
            }
            if (webRecord) {
                webRecord.model.load({ resId: thread.id });
            }
        },
        /**
         * Handles click on this "Done & Schedule Next" button.
         */
        async onClickDoneAndScheduleNext() {
            const chatter = this.activityViewOwner && this.activityViewOwner.chatterOwner;
            const reloadFunc = this.reloadFunc;
            const webRecord = this.webRecord;
            const thread = this.activity.thread;
            const activityListViewOwner =
                this.activityListViewItemOwner &&
                this.activityListViewItemOwner.activityListViewOwner;
            const activity = this.activity;
            const feedback = this.feedbackTextareaRef.el.value;
            if (activityListViewOwner && activityListViewOwner.exists()) {
                activityListViewOwner.popoverViewOwner.delete();
            }
            await activity.markAsDoneAndScheduleNext({ feedback });
            if (chatter && chatter.exists() && chatter.component) {
                chatter.reloadParentView();
            }
            if (reloadFunc) {
                reloadFunc();
            }
            if (webRecord) {
                webRecord.model.load({ resId: thread.id });
            }
        },
        /**
         * Handles keydown on this activity mark done.
         */
        onKeydown(ev) {
            if (ev.key === "Escape") {
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
                this.activityListViewItemOwner.update({ markDoneView: clear() });
                return;
            }
        },
    },
    fields: {
        activity: one("Activity", {
            required: true,
            compute() {
                if (this.activityListViewItemOwner) {
                    return this.activityListViewItemOwner.activity;
                }
                if (this.activityViewOwner) {
                    return this.activityViewOwner.activity;
                }
                return clear();
            },
        }),
        activityListViewItemOwner: one("ActivityListViewItem", {
            identifying: true,
            inverse: "markDoneView",
        }),
        activityViewOwner: one("ActivityView", {
            compute() {
                if (this.popoverViewOwner && this.popoverViewOwner.activityViewOwnerAsMarkDone) {
                    return this.popoverViewOwner.activityViewOwnerAsMarkDone;
                }
                return clear();
            },
        }),
        feedbackTextareaRef: attr({ ref: "feedbackTextarea" }),
        hasHeader: attr({
            compute() {
                return Boolean(this.popoverViewOwner);
            },
        }),
        headerText: attr({
            compute() {
                if (this.activityViewOwner) {
                    return this.activityViewOwner.markDoneText;
                }
                return this.env._t("Mark Done");
            },
        }),
        popoverViewOwner: one("PopoverView", {
            identifying: true,
            inverse: "activityMarkDonePopoverContentView",
        }),
        reloadFunc: attr({
            compute() {
                if (this.activityListViewItemOwner) {
                    return this.activityListViewItemOwner.reloadFunc;
                }
                return clear();
            },
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
