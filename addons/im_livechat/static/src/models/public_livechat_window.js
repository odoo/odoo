/** @odoo-module **/

import PublicLivechatWindow from '@im_livechat/legacy/widgets/public_livechat_window/public_livechat_window';

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'PublicLivechatWindow',
    identifyingFields: ['livechatButtonViewOwner'],
    lifecycleHooks: {
        _willDelete() {
            if (this.legacyChatWindow) {
                this.legacyChatWindow.destroy();
            }
        },
    },
    recordMethods: {
        /**
         * @private
         * @returns {im_livechat/legacy/widgets/public_chat_window|FieldCommand}
         */
        _computeLegacyChatWindow() {
            if (!this.livechatButtonViewOwner.widget && this.legacyChatWindow) {
                this.legacyChatWindow.destroy();
                return clear();
            }
            return new PublicLivechatWindow(
                this.livechatButtonViewOwner.widget,
                this.messaging.livechatButtonView.publicLivechat.legacyPublicLivechat,
                {
                    displayStars: false,
                    headerBackgroundColor: this.livechatButtonViewOwner.headerBackgroundColor,
                    placeholder: this.livechatButtonViewOwner.inputPlaceholder,
                    titleColor: this.livechatButtonViewOwner.titleColor,
                },
            );
        },
    },
    fields: {
        legacyChatWindow: attr({
            compute: '_computeLegacyChatWindow',
            default: null,
        }),
        livechatButtonViewOwner: one('LivechatButtonView', {
            inverse: 'chatWindow',
            readonly: true,
            required: true,
        }),
    },
});
