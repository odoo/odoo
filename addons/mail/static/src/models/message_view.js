/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear, insertAndReplace, replace } from '@mail/model/model_field_command';
import { markEventHandled } from '@mail/utils/utils';

registerModel({
    name: 'MessageView',
    identifyingFields: [['threadView', 'deleteMessageConfirmViewOwner'], 'message'],
    recordMethods: {
        /**
         * Briefly highlights the message.
         */
        highlight() {
            this.messaging.browser.clearTimeout(this.highlightTimeout);
            this.update({
                isHighlighted: true,
                highlightTimeout: this.messaging.browser.setTimeout(() => {
                    if (!this.exists()) {
                        return;
                    }
                    this.update({ isHighlighted: false });
                }, 2000),
            });
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickFailure(ev) {
            markEventHandled(ev, 'Message.ClickFailure');
            this.message.openResendAction();
        },
        onComponentUpdate() {
            if (!this.exists()) {
                return;
            }
            if (this.doHighlight && this.component && this.component.root.el) {
                this.component.root.el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                this.highlight();
                this.update({ doHighlight: clear() });
            }
            if (this.threadView && this.threadView.lastMessageView === this && this.component && this.component.isPartiallyVisible()) {
                this.threadView.handleVisibleMessage(this.message);
            }
        },
        /**
         * Action to initiate reply to current messageView.
         */
        replyTo() {
            // When already replying to this messageView, discard the reply.
            if (this.threadView.replyingToMessageView === this) {
                this.threadView.composerView.discard();
                return;
            }
            this.message.originThread.update({
                composer: insertAndReplace({
                    isLog: !this.message.is_discussion && !this.message.is_notification,
                }),
            });
            this.threadView.update({
                replyingToMessageView: replace(this),
                composerView: insertAndReplace({
                    doFocus: true,
                }),
            });
        },
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
                    mentionedPartners: replace(this.message.recipients),
                    textInputContent,
                    textInputCursorEnd: textInputContent.length,
                    textInputCursorStart: textInputContent.length,
                    textInputSelectionDirection: 'none',
                }),
                composerViewInEditing: insertAndReplace({
                    doFocus: true,
                }),
            });
        },
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
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeAttachmentList() {
            return (this.message && this.message.attachments.length > 0)
                ? insertAndReplace()
                : clear();
        },
        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computeExtraClass() {
            if (this.threadView) {
                return 'o_MessageList_item o_MessageList_message';
            }
            return clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeMessageActionList() {
            return this.deleteMessageConfirmViewOwner ? clear() : insertAndReplace();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeMessageInReplyToView() {
            return (
                this.message &&
                this.message.originThread &&
                this.message.originThread.model === 'mail.channel' &&
                this.message.parentMessage
            ) ? insertAndReplace() : clear();
        },
    },
    fields: {
        /**
         * Determines the attachment list displaying the attachments of this
         * message (if any).
         */
        attachmentList: one('AttachmentList', {
            compute: '_computeAttachmentList',
            inverse: 'messageViewOwner',
            isCausal: true,
            readonly: true,
        }),
        /**
         * States the component displaying this message view (if any).
         */
        component: attr(),
        composerForEditing: one('Composer', {
            inverse: 'messageViewInEditing',
            isCausal: true,
        }),
        /**
        * Determines the composer that is used to edit this message (if any).
        */
        composerViewInEditing: one('ComposerView', {
            inverse: 'messageViewInEditing',
            isCausal: true,
        }),
        /**
         * States the delete message confirm view that is displaying this
         * message view.
         */
        deleteMessageConfirmViewOwner: one('DeleteMessageConfirmView', {
            inverse: 'messageView',
            readonly: true,
        }),
        /**
         * Determines whether this message view should be highlighted at next
         * render. Scrolls into view and briefly highlights it.
         */
        doHighlight: attr(),
        /**
         * Determines which extra class this message view component should have.
         */
        extraClass: attr({
            compute: '_computeExtraClass',
            default: '',
        }),
        /**
         * id of the current timeout that will reset isHighlighted to false.
         */
        highlightTimeout: attr(),
        /**
         * Whether the message should be forced to be isHighlighted. Should only
         * be set through @see highlight()
         */
        isHighlighted: attr(),
        /**
         * Determines whether this message view should be squashed visually.
         */
        isSquashed: attr({
            default: false,
        }),
        /**
         * Determines the message action list of this message view (if any).
         */
        messageActionList: one('MessageActionList', {
            compute: '_computeMessageActionList',
            inverse: 'messageView',
            isCausal: true,
            readonly: true,
        }),
        /**
         * Determines the message that is displayed by this message view.
         */
        message: one('Message', {
            inverse: 'messageViews',
            readonly: true,
            required: true,
        }),
        /**
         * States the message in reply to view that displays the message of
         * which this message is a reply to (if any).
         */
        messageInReplyToView: one('MessageInReplyToView', {
            compute: '_computeMessageInReplyToView',
            inverse: 'messageView',
            isCausal: true,
            readonly: true,
        }),
        /**
         * States the thread view that is displaying this messages (if any).
         */
        threadView: one('ThreadView', {
            inverse: 'messageViews',
            readonly: true,
        }),
    },
});
