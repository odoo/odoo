/** @odoo-module **/

import PublicLivechatWindow from '@im_livechat/legacy/widgets/public_livechat_window/public_livechat_window';

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { insertAndReplace } from '@mail/model/model_field_command';

registerModel({
    name: 'PublicLivechatWindow',
    identifyingFields: ['livechatButtonViewOwner'],
    lifecycleHooks: {
        _created() {
            this.update({
                legacyChatWindow: new PublicLivechatWindow(
                    this.livechatButtonViewOwner.widget,
                    this.messaging,
                    this.messaging.publicLivechatGlobal.publicLivechat.legacyPublicLivechat,
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
            if (this.messaging.publicLivechatGlobal.livechatButtonView.inputPlaceholder) {
                return this.messaging.publicLivechatGlobal.livechatButtonView.inputPlaceholder;
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
        publicLivechatView: one('PublicLivechatView', {
            default: insertAndReplace(),
            inverse: 'publicLivechatWindowOwner',
            isCausal: true,
        }),
    },
});
