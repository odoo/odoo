/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

import PublicLivechatMessage from '@im_livechat/legacy/models/public_livechat_message';

registerModel({
    name: 'PublicLivechatMessage',
    lifecycleHooks: {
        _created() {
            this.update({ widget: new PublicLivechatMessage(this.messaging.publicLivechatGlobal.livechatButtonView.widget, this.messaging, this.data) });
        },
        _willDelete() {
            this.widget.destroy();
        },
    },
    recordMethods: {
        /**
         * @private
         * @returns {FieldCommand|integer}
         */
        _computeAuthorId() {
            if (!(this.data.author_id && this.data.author_id[0])) {
                return clear();
            }
            return this.data.author_id[0];
        },
    },
    fields: {
        authorId: attr({
            compute: '_computeAuthorId',
        }),
        data: attr(),
        id: attr({
            identifying: true,
        }),
        widget: attr(),
    },
});
