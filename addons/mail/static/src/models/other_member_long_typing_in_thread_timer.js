/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { insertAndReplace } from '@mail/model/model_field_command';

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
            default: insertAndReplace(),
            inverse: 'otherMemberLongTypingInThreadTimerOwner',
            isCausal: true,
            required: true,
        }),
    },
});
