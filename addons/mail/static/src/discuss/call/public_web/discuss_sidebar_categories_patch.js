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
            "rounded-bottom-0 border-bottom-0 o-ongoingCall border border-dark":
                this.thread.rtcSessions.length > 0,
        };
    },
});
