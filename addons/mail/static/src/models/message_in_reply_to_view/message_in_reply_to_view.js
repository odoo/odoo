/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, one2one } from '@mail/model/model_field';
import { clear, replace } from '@mail/model/model_field_command';
import { markEventHandled } from '@mail/utils/utils';

function factory(dependencies) {

    class MessageInReplyToView extends dependencies['mail.model'] {

        /**
         * @override
         */
        _created() {
            // bind handlers so they can be used in templates
            this.onClickReply = this.onClickReply.bind(this);
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

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
        }

    }

    MessageInReplyToView.fields = {
        messageView: one2one('mail.message_view', {
            inverse: 'messageInReplyToView',
            readonly: true,
            required: true,
        }),
    };
    MessageInReplyToView.identifyingFields = ['messageView'];
    MessageInReplyToView.modelName = 'mail.message_in_reply_to_view';

    return MessageInReplyToView;
}

registerNewModel('mail.message_in_reply_to_view', factory);
