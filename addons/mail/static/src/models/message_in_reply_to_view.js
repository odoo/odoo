/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { markEventHandled } from '@mail/utils/utils';

registerModel({
    name: 'MessageInReplyToView',
    recordMethods: {
        /**
         * @private
         * @param {MouseEvent} ev
         */
        async onClickReply(ev) {
            markEventHandled(ev, 'MessageInReplyToView.ClickMessageInReplyTo');
            const messageListViewItem = this.messageView && this.messageView.messageListViewItemOwner;
            const parentMessage = this.messageView.message.parentMessage;
            if (!messageListViewItem || !parentMessage) {
                return;
            }
            if (parentMessage.originThread !== messageListViewItem.messageListViewOwner.thread) {
                if (!parentMessage.originThread.isPinned) {
                    this.messaging.notify({
                        message: this.env._t("You have already left the channel. Please rejoin."),
                        type: 'warning',
                    });
                } else {
                    parentMessage.originThread.update({ pendingHighlightMessage: parentMessage });
                    await parentMessage.originThread.open();
                }
                return;
            }
            const parentMessageListViewItem = this.messaging.models['MessageListViewItem'].findFromIdentifyingData({
                message: parentMessage,
                messageListViewOwner: messageListViewItem.messageListViewOwner,
            });
            if (!parentMessageListViewItem) {
                return;
            }
            parentMessageListViewItem.messageView.update({ doHighlight: true });
        },
    },
    fields: {
        /**
         * Determines if the reply has a back link to an attachment only
         * message.
         */
        hasAttachmentBackLink: attr({
            compute() {
                const parentMessage = this.messageView.message.parentMessage;
                return parentMessage.isBodyEmpty && parentMessage.hasAttachments;
            },
        }),
        /**
         * Determines if the reply has a back link to a non-empty body.
         */
        hasBodyBackLink: attr({
            compute() {
                return !this.messageView.message.parentMessage.isBodyEmpty;
            },
        }),
        messageView: one('MessageView', {
            identifying: true,
            inverse: 'messageInReplyToView',
        }),
    },
});
