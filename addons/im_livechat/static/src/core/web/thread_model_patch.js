import { Thread } from "@mail/core/common/thread_model";
import { fields } from "@mail/model/misc";
import { convertBrToLineBreak } from "@mail/utils/common/format";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    setup() {
        super.setup();
        this.hasFetchedLivechatSessionData = false;
        this.livechat_note = fields.Html();
        /** @type {string|undefined} */
        this.livechatNoteText = fields.Attr(undefined, {
            compute() {
                if (this.livechat_note !== undefined) {
                    return convertBrToLineBreak(this.livechat_note || "");
                }
                return this.livechatNoteText;
            },
        });
        /** @type {"no_answer"|"no_agent"|"no_failure"|"escalated"|undefined} */
        this.livechat_outcome = undefined;
    },
});
