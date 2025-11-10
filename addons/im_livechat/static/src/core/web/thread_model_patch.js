import { Thread } from "@mail/core/common/thread_model";
import { fields } from "@mail/model/misc";
import { convertBrToLineBreak } from "@mail/utils/common/format";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";

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
    get livechatStatusLabel() {
        if (this.livechat_end_dt) {
            return _t("Conversation has ended");
        }
        const status = this.livechat_status;
        if (status === "waiting") {
            return _t("Waiting for customer");
        } else if (status === "need_help") {
            return _t("Looking for help");
        }
        return _t("In progress");
    },
    /** @param {"in_progress"|"waiting"|"need_help"} status */
    updateLivechatStatus(status) {
        if (this.livechat_status === status) {
            return;
        }
        rpc("/im_livechat/session/update_status", { channel_id: this.id, livechat_status: status });
    },
});
