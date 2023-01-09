/** @odoo-module **/

import { one, Model } from "@mail/model";

Model({
    name: "OtherMemberLongTypingInThreadTimer",
    recordMethods: {
        onOtherMemberLongTypingTimeout() {
            this.thread.unregisterOtherMemberTypingMember(this.member);
        },
    },
    fields: {
        member: one("ChannelMember", {
            identifying: true,
            inverse: "otherMemberLongTypingInThreadTimers",
        }),
        thread: one("Thread", { identifying: true, inverse: "otherMembersLongTypingTimers" }),
        timer: one("Timer", {
            default: {},
            inverse: "otherMemberLongTypingInThreadTimerOwner",
            required: true,
        }),
    },
});
