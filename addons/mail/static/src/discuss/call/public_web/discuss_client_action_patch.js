import { DiscussClientAction } from "@mail/core/public_web/discuss_client_action";

import { browser } from "@web/core/browser/browser";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

patch(DiscussClientAction.prototype, {
    setup() {
        super.setup(...arguments);
        this.rtc = useService("discuss.rtc");
    },
    /**
     * Checks if we are in a client action and if we have a query parameter requesting to join a call,
     * if so, the call is joined on the current discuss thread.
     */
    async restoreDiscussThread() {
        const hasFullScreenUrl = new URL(browser.location.href).searchParams.has("fullscreen");
        await super.restoreDiscussThread(...arguments);
        const action = this.props.action;
        if (!action) {
            return;
        }
        const call = action.context?.call || action.params?.call;
        if (call === "accept") {
            await this.rtc.joinCall(this.store.discuss.thread);
            return;
        }
        if (
            hasFullScreenUrl &&
            this.store.discuss.thread?.default_display_mode === "video_full_screen" &&
            this.store.discuss.thread.rtc_session_ids.length > 0
        ) {
            this.joinCallWithDefaultSettings();
        }
    },
    async joinCallWithDefaultSettings() {
        const mute = browser.localStorage.getItem("discuss_call_preview_join_mute") === "true";
        const camera = browser.localStorage.getItem("discuss_call_preview_join_video") === "true";
        await this.rtc.toggleCall(this.store.discuss.thread, { audio: !mute, camera });
        await this.rtc.enterFullscreen();
    },
});
