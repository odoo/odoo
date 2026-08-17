import { DiscussContent } from "@mail/core/public_web/discuss_content";

import { patch } from "@web/core/utils/patch";

patch(DiscussContent.prototype, {
    get inMeetingEndText() {
        return this.thread?.channel?.correspondentPartner?.inMeetingEndText;
    },
    get hasHeaderSubline() {
        return super.hasHeaderSubline || Boolean(this.inMeetingEndText);
    },
});
