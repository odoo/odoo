/** @odoo-module **/

import Feedback from '@im_livechat/legacy/widgets/feedback/feedback';

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'PublicLivechatFeedbackView',
    identifyingFields: ['publicLivechatGlobalOwner'],
    lifecycleHooks: {
        _created() {
            this.update({
                widget: new Feedback(
                    this.messaging.livechatButtonView.widget,
                    this.messaging.livechatButtonView.publicLivechat.legacyPublicLivechat,
                ),
            });
            this.messaging.livechatButtonView.chatWindow.legacyChatWindow.replaceContentWith(this.widget);
            this.widget.on('feedback_sent', null, this.onFeedbackSend);
            this.widget.on('send_message', null, this.onSendMessage);
        },
        _willDelete() {
            this.widget.destroy();
        },
    },
    recordMethods: {
        onFeedbackSend(...args) {
            this.messaging.livechatButtonView.widget._closeChat(...args);
        },
        onSendMessage(...args) {
            this.messaging.livechatButtonView.widget._sendMessage(...args);
        },
    },
    fields: {
        publicLivechatGlobalOwner: one('PublicLivechatGlobal', {
            inverse: 'feedbackView',
            readonly: true,
            required: true,
        }),
        widget: attr(),
    },
});
