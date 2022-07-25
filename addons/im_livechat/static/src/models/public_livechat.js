/** @odoo-module **/

import PublicLivechat from '@im_livechat/legacy/models/public_livechat';

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear, insertAndReplace } from '@mail/model/model_field_command';

registerModel({
    name: 'PublicLivechat',
    identifyingFields: ['livechatButtonOwner'],
    lifecycleHooks: {
        _created() {
            this.update({
                legacyPublicLivechat: new PublicLivechat(this.messaging, {
                    parent: this.livechatButtonOwner.widget,
                    data: this.data,
                }),
            });
        },
        _willDelete() {
            this.legacyPublicLivechat.destroy();
        },
    },
    recordMethods: {
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeOperator() {
            if (!this.data) {
                return clear();
            }
            if (!this.data.operator_pid) {
                return clear();
            }
            if (!this.data.operator_pid[0]) {
                return clear();
            }
            return insertAndReplace({
                id: this.data.operator_pid[0],
                name: this.data.operator_pid[1],
            });
        },
    },
    fields: {
        data: attr(),
        legacyPublicLivechat: attr(),
        livechatButtonOwner: one('LivechatButtonView', {
            inverse: 'publicLivechat',
            readonly: true,
            required: true,
        }),
        messages: many('PublicLivechatMessage'),
        operator: one('LivechatOperator', {
            compute: '_computeOperator',
        }),
        // amount of messages that have not yet been read on this chat
        unreadCounter: attr({
            default: 0,
        }),
    },
});
