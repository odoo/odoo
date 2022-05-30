/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'CallInviteRequestPopup',
    identifyingFields: ['thread'],
    recordMethods: {
        /**
         * @param {MouseEvent} ev
         */
        onClickRefuse(ev) {
            if (this.thread.hasPendingRtcRequest) {
                return;
            }
            this.thread.leaveCall();
        },
        /**
         * @param {MouseEvent} ev
         */
        async onClickAccept(ev) {
            this.thread.open();
            if (this.thread.hasPendingRtcRequest) {
                return;
            }
            await this.thread.toggleCall();
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickAvatar(ev) {
            this.thread.open();
        },
    },
    fields: {
        thread: one('Thread', {
            inverse: 'callInviteRequestPopup',
            readonly: true,
            required: true,
        }),
    },
});
