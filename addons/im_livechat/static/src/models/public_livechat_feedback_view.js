/** @odoo-module **/

import Feedback from '@im_livechat/legacy/widgets/feedback/feedback';

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'PublicLivechatFeedbackView',
    lifecycleHooks: {
        _created() {
            this.update({
                widget: new Feedback(
                    this.messaging.publicLivechatGlobal.livechatButtonView.widget,
                    this.messaging,
                    this.messaging.publicLivechatGlobal.publicLivechat.legacyPublicLivechat,
                ),
            });
            this.messaging.publicLivechatGlobal.livechatButtonView.chatWindow.legacyChatWindow.replaceContentWith(this.widget);
            this.widget.on('feedback_sent', null, this._onFeedbackSent);
            this.widget.on('send_message', null, this._onSendMessage);
        },
        _willDelete() {
            this.widget.destroy();
        },
    },
    recordMethods: {
        _onFeedbackSent() {
            this.messaging.publicLivechatGlobal.livechatButtonView.closeChat();
        },
        _onSendMessage(...args) {
            this.messaging.publicLivechatGlobal.livechatButtonView.sendMessage(...args);
        },
    },
    fields: {
        publicLivechatGlobalOwner: one('PublicLivechatGlobal', {
            identifying: true,
            inverse: 'feedbackView',
            readonly: true,
            required: true,
        }),
        widget: attr(),
    },
});
