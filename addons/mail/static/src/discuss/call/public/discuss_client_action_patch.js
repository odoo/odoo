import { DiscussClientAction } from "@mail/core/public_web/discuss_client_action";
import { useState } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

patch(DiscussClientAction.prototype, {
    setup() {
        super.setup(...arguments);
        this.rtc = useState(useService("discuss.rtc"));
    },
    async restoreDiscussThread() {
        await super.restoreDiscussThread(...arguments);
        if (!this.store.discuss.thread) {
            return;
        }
        const video = browser.localStorage.getItem("discuss_call_preview_join_video");
        const mute = browser.localStorage.getItem("discuss_call_preview_join_mute");
        if (this.store.discuss_public_thread.defaultDisplayMode === "video_full_screen") {
            this.rtc.toggleCall(this.store.discuss_public_thread, { video }).then(() => {
                if (mute) {
                    this.rtc.toggleMicrophone();
                }
            });
        }
    },
});
