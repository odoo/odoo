/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'OtherMemberLongTypingInThreadTimer',
    recordMethods: {
        onOtherMemberLongTypingTimeout() {
            this.thread.unregisterOtherMemberTypingMember(this.partner);
        },
    },
    fields: {
        partner: one('Partner', {
            identifying: true,
            inverse: 'otherMemberLongTypingInThreadTimers',
        }),
        thread: one('Thread', {
            identifying: true,
            inverse: 'otherMembersLongTypingTimers',
        }),
        timer: one('Timer', {
            default: {},
            inverse: 'otherMemberLongTypingInThreadTimerOwner',
            isCausal: true,
            required: true,
        }),
    },
});
