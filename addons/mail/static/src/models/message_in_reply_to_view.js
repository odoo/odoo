/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { replace } from '@mail/model/model_field_command';
import { markEventHandled } from '@mail/utils/utils';

registerModel({
    name: 'MessageInReplyToView',
    identifyingFields: ['messageView'],
    recordMethods: {
        /**
         * @private
         * @param {MouseEvent} ev
         */
        onClickReply(ev) {
            markEventHandled(ev, 'MessageInReplyToView.ClickMessageInReplyTo');
            const threadView = this.messageView && this.messageView.messageListViewMessageViewItemOwner && this.messageView.messageListViewMessageViewItemOwner.messageListViewOwner.threadViewOwner;
            const parentMessage = this.messageView.message.parentMessage;
            if (!threadView || !parentMessage) {
                return;
            }
            const parentMessageView = this.messaging.models['MessageView'].findFromIdentifyingData({
                message: replace(parentMessage),
                threadView: replace(threadView),
            });
            if (!parentMessageView) {
                return;
            }
            parentMessageView.update({ doHighlight: true });
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
            inverse: 'messageInReplyToView',
            readonly: true,
            required: true,
        }),
    },
});
