/** @odoo-module **/

import PublicLivechat from '@im_livechat/legacy/models/public_livechat';

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear, insertAndReplace } from '@mail/model/model_field_command';

registerModel({
    name: 'PublicLivechat',
    lifecycleHooks: {
        _created() {
            this.update({
                legacyPublicLivechat: new PublicLivechat(this.messaging, {
                    parent: this.publicLivechatGlobalOwner.livechatButtonView.widget,
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
         * @returns {integer|FieldCommand}
         */
        _computeId() {
            if (!this.data) {
                return clear();
            }
            return this.data.id;
        },
        /**
         * @private
         * @returns {FieldCommand|string}
         */
        _computeName() {
            if (!this.data) {
                return clear();
            }
            return this.data.name;
        },
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
        /**
         * @private
         * @returns {FieldCommand|string}
         */
        _computeStatus() {
            if (!this.data) {
                return clear();
            }
            return this.data.status || '';
        },
        /**
         * @private
         * @returns {FieldCommand|string}
         */
        _computeUuid() {
            if (!this.data) {
                return clear();
            }
            return this.data.uuid;
        },
    },
    fields: {
        data: attr(),
        id: attr({
            compute: '_computeId',
        }),
        isFolded: attr({
            default: false,
        }),
        legacyPublicLivechat: attr(),
        publicLivechatGlobalOwner: one('PublicLivechatGlobal', {
            identifying: true,
            inverse: 'publicLivechat',
        }),
        name: attr({
            compute: '_computeName',
        }),
        operator: one('LivechatOperator', {
            compute: '_computeOperator',
        }),
        status: attr({
            compute: '_computeStatus',
        }),
        // amount of messages that have not yet been read on this chat
        unreadCounter: attr({
            default: 0,
        }),
        uuid: attr({
            compute: '_computeUuid',
        }),
    },
});
