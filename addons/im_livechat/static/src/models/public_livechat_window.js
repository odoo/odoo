/** @odoo-module **/

import PublicLivechatWindow from '@im_livechat/legacy/widgets/public_livechat_window/public_livechat_window';

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'PublicLivechatWindow',
    lifecycleHooks: {
        _created() {
            this.update({
                widget: new PublicLivechatWindow(
                    this.messaging.publicLivechatGlobal.livechatButtonView.widget,
                    this.messaging,
                    this.messaging.publicLivechatGlobal.publicLivechat.legacyPublicLivechat,
                ),
            });
        },
        _willDelete() {
            this.widget.destroy();
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
        publicLivechatGlobalOwner: one('PublicLivechatGlobal', {
            identifying: true,
            inverse: 'chatWindow',
        }),
        publicLivechatView: one('PublicLivechatView', {
            default: {},
            inverse: 'publicLivechatWindowOwner',
            isCausal: true,
        }),
        widget: attr(),
    },
});
