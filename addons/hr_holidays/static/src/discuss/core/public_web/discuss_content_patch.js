import { DiscussContent } from "@mail/core/public_web/discuss_content";

import { patch } from "@web/core/utils/patch";

patch(DiscussContent.prototype, {
    get outOfOfficeDateEndText() {
        return this.thread?.channel?.correspondent?.partner_id?.outOfOfficeDateEndText;
    },
    get hasHeaderSubline() {
        return super.hasHeaderSubline || Boolean(this.outOfOfficeDateEndText);
    },
});
