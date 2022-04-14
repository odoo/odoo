/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'RtcInvitationCard',
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
    },
    fields: {
        thread: one('Thread', {
            inverse: 'rtcInvitationCard',
            readonly: true,
            required: true,
        }),
    },
});
