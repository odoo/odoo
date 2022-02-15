/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'ActivityMarkDonePopoverView',
    identifyingFields: ['activityViewOwner'],
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
            const { chatter } = this.activityViewOwner.activityBoxView;
            await this.activityViewOwner.activity.markAsDone({
                feedback: this.feedbackTextareaRef.el.value,
            });
            if (!chatter.exists() || !chatter.component) {
                return;
            }
            chatter.reloadParentView();
        },
        /**
         * Handles click on this "Done & Schedule Next" button.
         */
        async onClickDoneAndScheduleNext() {
            const { chatter } = this.activityViewOwner.activityBoxView;
            await this.activityViewOwner.activity.markAsDoneAndScheduleNext({
                feedback: this.feedbackTextareaRef.el.value,
            });
            if (!chatter.exists() || !chatter.component) {
                return;
            }
            chatter.reloadParentView();
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
            this.activityViewOwner.activity.update({
                feedbackBackup: this.feedbackTextareaRef.el.value,
            });
        },
        /**
         * @private
         */
        _close() {
            this._backupFeedback();
            this.component.trigger('o-popover-close');
        },
    },
    fields: {
        activityViewOwner: one('ActivityView', {
            inverse: 'activityMarkDonePopoverView',
            readonly: true,
            required: true,
        }),
        component: attr(),
        feedbackTextareaRef: attr(),
    },
});
