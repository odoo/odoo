/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { isEventHandled } from '@mail/utils/utils';

registerModel({
    name: 'ChatWindowHeaderView',
    recordMethods: {
        /**
         * @param {MouseEvent} ev
         */
        onClick(ev) {
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
            readonly: true,
            required: true,
        }),
    },
});
