/** @odoo-module **/

import PublicLivechat from '@im_livechat/legacy/models/public_livechat';

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'PublicLivechat',
    lifecycleHooks: {
        _created() {
            this.update({
                widget: new PublicLivechat(this.messaging, {
                    parent: this.publicLivechatGlobalOwner.livechatButtonView.widget,
                    data: this.data,
                }),
            });
        },
        _willDelete() {
            this.widget.destroy();
        },
    },
    fields: {
        data: attr(),
        id: attr({
            compute() {
                if (!this.data) {
                    return clear();
                }
                return this.data.id;
            },
        }),
        isFolded: attr({
            default: false,
        }),
        publicLivechatGlobalOwner: one('PublicLivechatGlobal', {
            identifying: true,
            inverse: 'publicLivechat',
        }),
        name: attr({
            compute() {
                if (!this.data) {
                    return clear();
                }
                return this.data.name;
            },
        }),
        operator: one('LivechatOperator', {
            compute() {
                if (!this.data) {
                    return clear();
                }
                if (!this.data.operator_pid) {
                    return clear();
                }
                if (!this.data.operator_pid[0]) {
                    return clear();
                }
                return {
                    id: this.data.operator_pid[0],
                    name: this.data.operator_pid[1],
                };
            },
        }),
        status: attr({
            compute() {
                if (!this.data) {
                    return clear();
                }
                return this.data.status || '';
            },
        }),
        // amount of messages that have not yet been read on this chat
        unreadCounter: attr({
            default: 0,
        }),
        uuid: attr({
            compute() {
                if (!this.data) {
                    return clear();
                }
                return this.data.uuid;
            },
        }),
        widget: attr(),
    },
});
