/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { insertAndReplace } from '@mail/model/model_field_command';

registerModel({
    name: 'OtherMemberLongTypingInThreadTimer',
    identifyingFields: [
        'partner',
        'thread',
    ],
    recordMethods: {
        onOtherMemberLongTypingTimeout() {
            this.thread.unregisterOtherMemberTypingMember(this.partner);
        },
    },
    fields: {
        partner: one('Partner', {
            inverse: 'otherMemberLongTypingInThreadTimers',
            readonly: true,
            required: true,
        }),
        thread: one('Thread', {
            inverse: 'otherMembersLongTypingTimers',
            readonly: true,
            required: true,
        }),
        timer: one('Timer', {
            default: insertAndReplace(),
            inverse: 'otherMemberLongTypingInThreadTimerOwner',
            isCausal: true,
            required: true,
        }),
    },
});
