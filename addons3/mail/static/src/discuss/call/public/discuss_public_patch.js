/* @odoo-module */

import { DiscussPublic } from "@mail/discuss/core/public/discuss_public";
import { useState } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

patch(DiscussPublic.prototype, {
    setup() {
        super.setup(...arguments);
        this.rtc = useState(useService("discuss.rtc"));
    },
    async displayChannel() {
        super.displayChannel();
        const video = browser.localStorage.getItem("discuss_call_preview_join_video");
        const mute = browser.localStorage.getItem("discuss_call_preview_join_mute");
        if (this.thread.defaultDisplayMode === "video_full_screen") {
            this.rtc.toggleCall(this.thread, { video }).then(() => {
                if (mute) {
                    this.rtc.toggleMicrophone();
                }
            });
        }
    },
});
