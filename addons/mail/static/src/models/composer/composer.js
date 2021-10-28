/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, many2one, one2many, one2one } from '@mail/model/model_field';
import { clear, insertAndReplace, replace } from '@mail/model/model_field_command';

function factory(dependencies) {

    class Composer extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @returns {mail.thread}
         */
        _computeActiveThread() {
            if (this.messageViewInEditing && this.messageViewInEditing.message && this.messageViewInEditing.message.originThread) {
                return replace(this.messageViewInEditing.message.originThread);
            }
            if (this.thread) {
                return replace(this.thread);
            }
            return clear();
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeCanPostMessage() {
            if (this.thread && !this.textInputContent && this.messageComposition.attachments.length === 0) {
                return false;
            }
            return !this.hasUploadingAttachment && !this.isPostingMessage;
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeHasUploadingAttachment() {
            return this.messageComposition.attachments.some(attachment => attachment.isUploading);
        }

        /**
         * @private
         */
        _reset() {
            this.update({
                isLastStateChangeProgrammatic: true,
                messageComposition: clear(),
                textInputContent: clear(),
                textInputCursorEnd: clear(),
                textInputCursorStart: clear(),
                textInputSelectionDirection: clear(),
            });
        }

    }

    Composer.fields = {
        activeThread: many2one('mail.thread', {
            compute: '_computeActiveThread',
            readonly: true,
            required: true,
        }),
        canPostMessage: attr({
            compute: '_computeCanPostMessage',
            default: false,
        }),
        composerViews: one2many('mail.composer_view', {
            inverse: 'composer',
            isCausal: true,
        }),
        /**
         * This field determines whether some attachments linked to this
         * composer are being uploaded.
         */
        hasUploadingAttachment: attr({
            compute: '_computeHasUploadingAttachment',
        }),
        /**
         * Determines whether the last change (since the last render) was
         * programmatic. Useful to avoid restoring the state when its change was
         * from a user action, in particular to prevent the cursor from jumping
         * to its previous position after the user clicked on the textarea while
         * it didn't have the focus anymore.
         */
        isLastStateChangeProgrammatic: attr({
            default: false,
        }),
        /**
         * If true composer will log a note, else a comment will be posted.
         */
        isLog: attr({
            default: true,
        }),
        /**
         * Determines whether a post_message request is currently pending.
         */
        isPostingMessage: attr(),
        messageComposition: one2one('mail.message_composition', {
            default: insertAndReplace(),
            inverse: 'composer',
            isCausal: true,
        }),
        messageViewInEditing: one2one('mail.message_view', {
            inverse: 'composerForEditing',
            readonly: true,
        }),
        /**
         * Determines the extra `mail.partner` (on top of existing followers)
         * that will receive the message being composed by `this`, and that will
         * also be added as follower of `this.activeThread`.
         */
        textInputContent: attr({
            default: "",
        }),
        textInputCursorEnd: attr({
            default: 0,
        }),
        textInputCursorStart: attr({
            default: 0,
        }),
        textInputSelectionDirection: attr({
            default: "none",
        }),
        /**
         * States the thread which this composer represents the state (if any).
         */
        thread: one2one('mail.thread', {
            inverse: 'composer',
            readonly: true,
        }),
    };
    Composer.identifyingFields = [['thread', 'messageViewInEditing']];
    Composer.modelName = 'mail.composer';

    return Composer;
}

registerNewModel('mail.composer', factory);
