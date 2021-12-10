/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one2one } from '@mail/model/model_field';
import { replace } from '@mail/model/model_field_command';
import { markEventHandled } from '@mail/utils/utils';

registerModel({
    name: 'mail.message_in_reply_to_view',
    identifyingFields: ['messageView'],
    lifecycleHooks: {
        _created() {
            // bind handlers so they can be used in templates
            this.onClickReply = this.onClickReply.bind(this);
        },
    },
    recordMethods: {
        /**
         * @private
         * @param {MouseEvent} ev
         */
        onClickReply(ev) {
            markEventHandled(ev, 'MessageInReplyToView.ClickMessageInReplyTo');
            const threadView = this.messageView && this.messageView.threadView;
            const parentMessage = this.messageView.message.parentMessage;
            if (!threadView || !parentMessage) {
                return;
            }
            const parentMessageView = this.messaging.models['mail.message_view'].findFromIdentifyingData({
                message: replace(parentMessage),
                threadView: replace(threadView),
            });
            if (!parentMessageView) {
                return;
            }
            threadView.addComponentHint('highlight-reply', parentMessageView);
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
        messageView: one2one('mail.message_view', {
            inverse: 'messageInReplyToView',
            readonly: true,
            required: true,
        }),
    },
});
