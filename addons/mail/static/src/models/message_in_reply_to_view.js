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
        onClickReply(ev) {
            markEventHandled(ev, 'MessageInReplyToView.ClickMessageInReplyTo');
            const messageListViewItem = this.messageView && this.messageView.messageListViewItemOwner;
            const parentMessage = this.messageView.message.parentMessage;
            if (!messageListViewItem || !parentMessage) {
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
        /**
         * @private
         * @returns {boolean}
         */
        _computeHasAttachmentBackLink() {
            const parentMessage = this.messageView.message.parentMessage;
            return parentMessage.isBodyEmpty && parentMessage.hasAttachments;
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeHasBodyBackLink() {
            return !this.messageView.message.parentMessage.isBodyEmpty;
        },
    },
    fields: {
        /**
         * Determines if the reply has a back link to an attachment only
         * message.
         */
        hasAttachmentBackLink: attr({
            compute: '_computeHasAttachmentBackLink',
        }),
        /**
         * Determines if the reply has a back link to a non-empty body.
         */
        hasBodyBackLink: attr({
            compute: '_computeHasBodyBackLink',
        }),
        messageView: one('MessageView', {
            identifying: true,
            inverse: 'messageInReplyToView',
        }),
    },
});
