import { ThreadIcon } from "@mail/core/common/thread_icon";
import { _t } from "@web/core/l10n/translation";

import { patch } from "@web/core/utils/patch";

patch(ThreadIcon.prototype, {
    get defaultChatIcon() {
        if (this.props.thread.channel_type === "livechat") {
            return { class: "fa fa-comments opacity-75", title: _t("Livechat") };
        }
        return super.defaultChatIcon;
    },
});
