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
        this.livechat_status = undefined;
        this.livechat_note = fields.Html();
        this.livechatNoteText = fields.Attr(undefined, {
            compute() {
                if (this.livechat_note !== undefined) {
                    return convertBrToLineBreak(this.livechat_note || "");
                }
                return this.livechatNoteText;
            },
        });
        this.livechat_expertise_ids = fields.Many("im_livechat.expertise");
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
    updateLivechatStatus(status) {
        if (this.livechat_status === status) {
            return;
        }
        rpc("/im_livechat/session/update_status", { channel_id: this.id, livechat_status: status });
    },
});
