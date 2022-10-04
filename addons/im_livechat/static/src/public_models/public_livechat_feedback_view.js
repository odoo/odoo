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
                    this.global.PublicLivechatGlobal.livechatButtonView.widget,
                    this.global.Messaging,
                    this.global.PublicLivechatGlobal.publicLivechat.widget,
                ),
            });
            this.global.PublicLivechatGlobal.chatWindow.widget.replaceContentWith(this.widget);
            this.widget.on('feedback_sent', null, this._onFeedbackSent);
            this.widget.on('send_message', null, this._onSendMessage);
        },
        _willDelete() {
            this.widget.destroy();
        },
    },
    recordMethods: {
        _onFeedbackSent() {
            this.global.PublicLivechatGlobal.livechatButtonView.closeChat();
        },
        _onSendMessage(...args) {
            this.global.PublicLivechatGlobal.livechatButtonView.sendMessage(...args);
        },
    },
    fields: {
        publicLivechatGlobalOwner: one('PublicLivechatGlobal', {
            identifying: true,
            inverse: 'feedbackView',
        }),
        widget: attr(),
    },
});
