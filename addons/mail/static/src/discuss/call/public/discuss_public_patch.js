/* @odoo-module */

import { DiscussPublic } from "@mail/discuss/core/public/discuss_public";
import { useRtc } from "@mail/discuss/call/common/rtc_hook";

import { browser } from "@web/core/browser/browser";
import { patch } from "@web/core/utils/patch";

patch(DiscussPublic.prototype, "discuss/call/public", {
    setup() {
        this._super(...arguments);
        this.rtc = useRtc();
    },
    async displayChannel() {
        this._super();
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
