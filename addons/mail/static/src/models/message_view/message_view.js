/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { clear, insertAndReplace } from '@mail/model/model_field_command';

import { attr, many2one, one2one } from '@mail/model/model_field';

function factory(dependencies) {

    class MessageView extends dependencies['mail.model'] {

        /**
         * Starts editing this message.
         */
        startEditing() {
            const parser = new DOMParser();
            const htmlDoc = parser.parseFromString(this.message.body.replaceAll('<br>', '\n').replaceAll('</br>', '\n'), "text/html");
            const textInputContent = htmlDoc.body.textContent;
            this.update({
                composerForEditing: insertAndReplace({
                    isLastStateChangeProgrammatic: true,
                    textInputContent,
                    textInputCursorEnd: textInputContent.length,
                    textInputCursorStart: textInputContent.length,
                    textInputSelectionDirection: 'none',
                }),
                composerViewInEditing: insertAndReplace({
                    doFocus: true,
                }),
            });
        }

        /**
         * Stops editing this message.
         */
        stopEditing() {
            if (this.threadView && this.threadView.composerView && !this.messaging.device.isMobileDevice) {
                this.threadView.composerView.update({ doFocus: true });
            }
            this.update({
                composerForEditing: clear(),
                composerViewInEditing: clear(),
            });
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeAttachmentList() {
            return (this.message && this.message.attachments.length > 0)
                ? insertAndReplace()
                : clear();
        }

        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeMessageActionList() {
            return (!this.messageActionListWithDelete)
                ? insertAndReplace()
                : clear();
        }

    }

    MessageView.fields = {
        /**
         * Determines the attachment list displaying the attachments of this
         * message (if any).
         */
        attachmentList: one2one('mail.attachment_list', {
            compute: '_computeAttachmentList',
            inverse: 'messageView',
            isCausal: true,
            readonly: true,
        }),
        /**
         * States the component displaying this message view (if any).
         */
        component: attr(),
        composerForEditing: one2one('mail.composer', {
            inverse: 'messageViewInEditing',
            isCausal: true,
        }),
        /**
        * Determines the composer that is used to edit this message (if any).
        */
        composerViewInEditing: one2one('mail.composer_view', {
            inverse: 'messageViewInEditing',
            isCausal: true,
        }),
        /**
         * Determines whether this message view should be squashed visually.
         */
        isSquashed: attr({
            default: false,
        }),
        /**
         * Determines the message action list of this message view (if any).
         */
        messageActionList: one2one('mail.message_action_list', {
            compute: '_computeMessageActionList',
            inverse: 'messageView',
            isCausal: true,
            readonly: true,
        }),
        /**
         * States the message action list that is displaying this message view
         * in its delete confirmation view.
         */
        messageActionListWithDelete: one2one('mail.message_action_list', {
            inverse: 'messageViewForDelete',
            isCausal: true,
            readonly: true,
        }),
        /**
         * Determines the message that is displayed by this message view.
         */
        message: many2one('mail.message', {
            inverse: 'messageViews',
            readonly: true,
            required: true,
        }),
        /**
         * States the thread view that is displaying this messages (if any).
         */
        threadView: many2one('mail.thread_view', {
            inverse: 'messageViews',
            readonly: true,
        }),
    };
    MessageView.identifyingFields = [['threadView', 'messageActionListWithDelete'], 'message'];
    MessageView.modelName = 'mail.message_view';

    return MessageView;
}

registerNewModel('mail.message_view', factory);
