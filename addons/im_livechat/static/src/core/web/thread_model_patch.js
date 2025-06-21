import { Thread } from "@mail/core/common/thread_model";
import { fields } from "@mail/model/misc";
import { convertBrToLineBreak } from "@mail/utils/common/format";
import { _t } from "@web/core/l10n/translation";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    setup() {
        super.setup();
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
    },
    get livechatStatusLabel() {
        const status = this.livechat_status;
        if (status === "waiting") {
            return _t("Waiting for customer");
        } else if (status === "need_help") {
            return _t("Looking for help");
        }
        return "";
    },
});
