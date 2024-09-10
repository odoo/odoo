import { DiscussSidebarCallParticipants } from "@mail/discuss/call/public_web/discuss_sidebar_call_participants";
import { DiscussSidebarChannel } from "@mail/discuss/core/public_web/discuss_sidebar_categories";
import { patch } from "@web/core/utils/patch";

DiscussSidebarChannel.components = Object.assign(DiscussSidebarChannel.components || {}, {
    DiscussSidebarCallParticipants,
});

patch(DiscussSidebarChannel.prototype, {
    get attClass() {
        return {
            ...super.attClass,
            "o-ongoingCall": this.thread.rtcSessions.length > 0,
        };
    },
    get hasChildren() {
        return super.hasChildren || this.thread.rtcSessions.length > 0;
    },
});
