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
            this.activityViewOwner.update({ markDonePopoverView: clear() });
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeActivityViewOwner() {
            if (this.popoverViewOwner.activityViewOwnerAsMarkDone) {
                return this.popoverViewOwner.activityViewOwnerAsMarkDone;
            }
            return clear();
        },
        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computeHeaderText() {
            if (this.activityViewOwner) {
                return this.activityViewOwner.markDoneText;
            }
            return clear();
        },
    },
    fields: {
        activityViewOwner: one('ActivityView', {
            compute: '_computeActivityViewOwner',
            readonly: true,
        }),
        component: attr(),
        feedbackTextareaRef: attr(),
        headerText: attr({
            compute: '_computeHeaderText',
            default: '',
        }),
        popoverViewOwner: one('PopoverView', {
            identifying: true,
            inverse: 'activityMarkDonePopoverContentView',
        }),
    },
});
