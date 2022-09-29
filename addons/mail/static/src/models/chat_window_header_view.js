/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';
import { isEventHandled } from '@mail/utils/utils';

registerModel({
    name: 'ChatWindowHeaderView',
    recordMethods: {
        /**
         * @param {MouseEvent} ev
         */
        onClick(ev) {
            if (!this.exists()) {
                return;
            }
            if (
                isEventHandled(ev, 'ChatWindow.onClickCommand') ||
                isEventHandled(ev, 'ChatWindow.onClickHideMemberList') ||
                isEventHandled(ev, 'ChatWindow.onClickShowMemberList')
            ) {
                return;
            }
            if (!this.chatWindowOwner.isVisible) {
                this.chatWindowOwner.onClickFromChatWindowHiddenMenu(ev);
            } else {
                this.chatWindowOwner.onClickHeader(ev);
            }
        },
    },
    fields: {
        chatWindowOwner: one('ChatWindow', {
            identifying: true,
            inverse: 'chatWindowHeaderView',
        }),
        threadIconView: one('ThreadIconView', {
            compute() {
                if (this.chatWindowOwner.thread && this.chatWindowOwner.thread.model === 'mail.channel') {
                    return {};
                }
                return clear();
            },
            inverse: 'chatWindowHeaderViewOwner',
        }),
    },
});
