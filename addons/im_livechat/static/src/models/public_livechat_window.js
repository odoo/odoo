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
                        titleColor: this.livechatButtonViewOwner.titleColor,
                    },
                ),
            });
        },
        _willDelete() {
            this.legacyChatWindow.destroy();
        },
    },
    recordMethods: {
        /**
         * @private
         * @returns {string}
         */
        _computeInputPlaceholder() {
            if (this.messaging.livechatButtonView.inputPlaceholder) {
                return this.messaging.livechatButtonView.inputPlaceholder;
            }
            return this.env._t("Say something");
        },
    },
    fields: {
        inputPlaceholder: attr({
            compute: '_computeInputPlaceholder',
        }),
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
