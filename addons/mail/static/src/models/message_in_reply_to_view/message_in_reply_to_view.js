/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one2one } from '@mail/model/model_field';
import { replace } from '@mail/model/model_field_command';
import { markEventHandled } from '@mail/utils/utils';

registerModel({
    name: 'MessageInReplyToView',
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
            const parentMessageView = this.messaging.models['MessageView'].findFromIdentifyingData({
                message: replace(parentMessage),
                threadView: replace(threadView),
            });
            if (!parentMessageView) {
                return;
            }
            threadView.addComponentHint('highlight-reply', parentMessageView);
        },
    },
    fields: {
        messageView: one2one('MessageView', {
            inverse: 'messageInReplyToView',
            readonly: true,
            required: true,
        }),
    },
});
