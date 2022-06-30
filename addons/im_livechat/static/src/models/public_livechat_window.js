/** @odoo-module **/

import PublicLivechatWindow from '@im_livechat/legacy/widgets/public_livechat_window/public_livechat_window';

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'PublicLivechatWindow',
    identifyingFields: ['livechatButtonViewOwner'],
    lifecycleHooks: {
        _created() {
            this.update({
                legacyChatWindow: new PublicLivechatWindow(
                    this.livechatButtonViewOwner.widget,
                    this.messaging,
                    this.messaging.livechatButtonView.publicLivechat.legacyPublicLivechat,
                    {
                        headerBackgroundColor: this.livechatButtonViewOwner.headerBackgroundColor,
                        placeholder: this.livechatButtonViewOwner.inputPlaceholder,
                        titleColor: this.livechatButtonViewOwner.titleColor,
                    },
                ),
            });
        },
        _willDelete() {
            this.legacyChatWindow.destroy();
        },
    },
    fields: {
        legacyChatWindow: attr({
            default: null,
        }),
        livechatButtonViewOwner: one('LivechatButtonView', {
            inverse: 'chatWindow',
            readonly: true,
            required: true,
        }),
    },
});
